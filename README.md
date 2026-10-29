# AI Jobs Market - MicroK8s HA

## 1. Objectif

Afficher les données du fichier AI Jobs Market 2025-2026 dans une page web, mettre l'application dans une image Docker, puis la faire tourner sur deux clusters MicroK8s séparés. Si un cluster tombe, l'autre continue de répondre.

## 2. Architecture

Deux VM Ubuntu 24.04 dans VirtualBox, une par cluster :

| VM | Cluster | IP | RAM / CPU |
|---|---|---|---|
| cluster-a-master | cluster A (1 nœud) | 192.168.168.10 | 2 Go / 2 |
| cluster-b-master | cluster B (1 nœud) | 192.168.168.20 | 2 Go / 2 |

Chaque VM a deux cartes réseau :
- carte 1 : réseau privé hôte VirtualBox (192.168.168.0/24), IP fixe
- carte 2 : NAT, pour Internet

Dans chaque cluster, namespace `ai-jobs` :
- Deployment `ai-jobs` (2 replicas) + Service NodePort 30080 + Ingress
- ConfigMap (nom du cluster) et Secret
- StatefulSet `redis-demo` avec ses PVC
- DaemonSet `node-agent-demo`
- Job `csv-check` et CronJob `health-report`

Pas de load balancer HAProxy : mon PC n'a que 16 Go de RAM. On accède à chaque cluster par son IP.

## 3. Prérequis

- VirtualBox 7
- Un réseau privé hôte en 192.168.168.0/24 (Fichier > Outils > Réseau)
- 2 VM Ubuntu 24.04 avec accès Internet par la carte NAT

## 4. Dataset

`data/ai_jobs_market_2025_2026.csv` : 1 500 offres, 25 colonnes. Le fichier est copié dans l'image Docker.

Vérification rapide avec pandas :

```
import pandas as pd
df = pd.read_csv("data/ai_jobs_market_2025_2026.csv")
print(df.shape)
print(df["annual_salary_usd"].mean())
```

Résultat attendu : `(1500, 25)` et `194892.0`.

## 5. Construction de l'image

```
docker build -t ai-jobs-dashboard:1.0 .
docker run --rm -p 8000:8000 ai-jobs-dashboard:1.0
curl http://localhost:8000/health
curl http://localhost:8000/api/stats
```

## 6. Cluster A

Sur la VM cluster-a-master :

```
sudo hostnamectl set-hostname cluster-a-master
sudo nmcli con add type ethernet ifname enp0s3 con-name hostonly ipv4.method manual ipv4.addresses 192.168.168.10/24 ipv4.never-default yes ipv6.method disabled
sudo nmcli con up hostonly
sudo snap install microk8s --classic --channel=1.35
sudo usermod -a -G microk8s $USER
sudo microk8s status --wait-ready
sudo microk8s enable dns
sudo microk8s enable hostpath-storage
sudo microk8s enable metrics-server
sudo microk8s enable ingress
```

Se déconnecter puis se reconnecter pour que le groupe `microk8s` soit pris en compte.

## 7. Cluster B

Même chose sur la VM cluster-b-master, avec le nom `cluster-b-master` et l'IP `192.168.168.20/24`.

Les deux clusters ne sont pas joints : chacun a son propre control plane.

## 8. Déploiement Kubernetes

Copier le dossier du projet sur la VM, puis :

```
sudo ./deploy.sh cluster-a
```

ou, sur la VM B :

```
sudo ./deploy.sh cluster-b
```

Le script :
1. construit l'image `ai-jobs-dashboard:1.0` avec Docker
2. l'importe dans MicroK8s avec `microk8s ctr image import` (pas de registre)
3. applique les YAML de `k8s/base` et ceux du cluster (`k8s/cluster-a` ou `k8s/cluster-b`)

Vérifier :

```
microk8s kubectl get all -n ai-jobs -o wide
```

## 9. HAProxy

Non réalisé (manque de RAM). Avec HAProxy, il faudrait une VM de plus qui teste `/health` sur 192.168.168.10:30080 et 192.168.168.20:30080, et qui envoie les clients vers le cluster en bonne santé.

## 10. Tests fonctionnels

Dans le navigateur :
- cluster A : http://192.168.168.10:30080
- cluster B : http://192.168.168.20:30080

En ligne de commande :

```
curl http://192.168.168.10:30080/health
curl http://192.168.168.10:30080/api/stats
curl "http://192.168.168.10:30080/api/stats?country=France"
curl "http://192.168.168.10:30080/api/jobs?category=Research"
```

Résultats attendus : `{"status":"ok"}`, 1500 offres, et 66 offres pour la France.

Tests Python :

```
pip install flask pandas pytest
python -m pytest tests
```

## 11. Tests de panne

Suppression d'un Pod (il doit être recréé) :

```
microk8s kubectl get pods -n ai-jobs
microk8s kubectl delete pod <nom-du-pod> -n ai-jobs
microk8s kubectl get pods -n ai-jobs -w
```

Perte d'un cluster complet. Sur la VM B, lancer la surveillance :

```
while true; do
  T=$(date +%T)
  A=$(curl -s -m 2 -o /dev/null -w "%{http_code}" http://192.168.168.10:30080/health)
  B=$(curl -s -m 2 -o /dev/null -w "%{http_code}" http://192.168.168.20:30080/health)
  echo "$T   cluster-a: $A   |   cluster-b: $B"
  sleep 2
done
```

Puis éteindre la VM A dans VirtualBox (Machine > Stop > Éteindre). A passe à `000`, B reste à `200`. Rallumer A : il revient à `200` après quelques minutes.

## 12. StatefulSet / DaemonSet

```
microk8s kubectl get statefulset,pvc -n ai-jobs
microk8s kubectl delete pod redis-demo-0 -n ai-jobs
microk8s kubectl get pods -n ai-jobs -l app=redis-demo -w
microk8s kubectl get daemonset -n ai-jobs
microk8s kubectl logs -l app=node-agent-demo -n ai-jobs --tail=5
```

`redis-demo-0` revient avec le même nom et le même PVC.

## 13. Observabilité

```
microk8s kubectl top nodes
microk8s kubectl top pods -n ai-jobs
microk8s kubectl logs deployment/ai-jobs -n ai-jobs --tail=20
microk8s kubectl get events -n ai-jobs --sort-by=.lastTimestamp
```

Chaque requête est écrite dans les logs avec la date, la route, le cluster, le Pod, le code HTTP et la durée.

## 14. Problèmes rencontrés

- **Pods en erreur au premier déploiement** : `PermissionError` sur le CSV. Le fichier n'était lisible que par root, et l'image tourne avec un utilisateur normal. Corrigé avec `chmod -R a+rX /app` dans le Dockerfile.
- **VM B injoignable** : la carte 1 était repassée en NAT. Corrigé dans VirtualBox (Périphériques > Réseau > Réseau privé hôte).
- **Copier-coller et clavier dans les VM** : il a fallu installer `virtualbox-guest-utils` et `virtualbox-guest-x11`, puis lancer `VBoxClient --clipboard`.
- **Groupe microk8s** : après `usermod`, il faut se reconnecter, sinon `microk8s kubectl` répond « Insufficient permissions ».
- **Redémarrage lent de A** : avec 2 Go de RAM, les Pods ont redémarré 9 fois au boot, car la liveness probe les tuait avant la fin du démarrage. Une `startupProbe` réglerait ça.

## 15. Limites et améliorations

- Un seul nœud par cluster : si la VM tombe, tout le cluster tombe.
- Pas de load balancer : la bascule d'un cluster à l'autre n'est pas automatique.
- `hostpath-storage` garde les données sur le disque du nœud : ce n'est pas un stockage HA.
- Le Secret est un exemple (`change-me`), il n'y a pas de TLS et pas de NetworkPolicy.
- À ajouter : HAProxy, un worker par cluster, une `startupProbe`, Prometheus/Grafana.

## Arborescence

```
ai-jobs-ha/
├── app/              code Flask (app.py, analytics.py, templates, static)
├── data/             CSV
├── k8s/
│   ├── base/         YAML communs aux 2 clusters
│   ├── cluster-a/    ConfigMap + Ingress du cluster A
│   └── cluster-b/    ConfigMap + Ingress du cluster B
├── tests/            tests pytest
├── docs/             rapport PDF et captures
├── Dockerfile
├── requirements.txt
├── deploy.sh
└── README.md
```
