# k8s_upgrade.py

import subprocess
import os
import sys

class K8sUpgradeManager:
    def _init_(self, version="1.32.3", dry_run=False):
        self.version = version
        self.dry_run = dry_run
    def run(self, cmd, check=True):
        print(f"\n➡️ {cmd}")
        if self.dry_run:
            print("🔸 Dry run: command not executed.")
            return ""
        result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
        if result.returncode != 0:
            print(f"❌ Error:\n{result.stderr}")
            if check:
                sys.exit(1)
        return result.stdout.strip()

    def backup_etcd(self, backup_path="/var/backups/etcd-snapshot.db"):
        print("📦 Backing up etcd...")
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        self.run(f"""
        ETCDCTL_API=3 etcdctl snapshot save {backup_path} \
        --endpoints=https://127.0.0.1:2379 \
        --cacert=/etc/kubernetes/pki/etcd/ca.crt \
        --cert=/etc/kubernetes/pki/etcd/server.crt \
        --key=/etc/kubernetes/pki/etcd/server.key
        """)

    def upgrade_kubeadm(self):
        print("⬆️ Upgrading kubeadm...")
        self.run("apt-mark unhold kubeadm")
        self.run(f"apt-get update && apt-get install -y kubeadm={self.version}-00")
        self.run("apt-mark hold kubeadm")

    def plan_upgrade(self):
        print("📋 Upgrade plan:")
        print(self.run("kubeadm upgrade plan", check=False))

    def apply_upgrade(self):
        print("🚀 Applying kubeadm upgrade...")
        self.run(f"kubeadm upgrade apply v{self.version} -y")

    def upgrade_kubelet_and_kubectl(self):
        print("⬆️ Upgrading kubelet and kubectl...")
        self.run("apt-mark unhold kubelet kubectl")
        self.run(f"apt-get install -y kubelet={self.version}-00 kubectl={self.version}-00")
        self.run("apt-mark hold kubelet kubectl")
        self.run("systemctl daemon-reexec && systemctl restart kubelet")

    def install_metrics_server(self):
        print("📊 Installing metrics-server...")
        self.run("kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml")

    def install_cluster_autoscaler(self):
        print("🤖 Installing cluster-autoscaler (generic config)...")
        self.run("kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/master/cluster-autoscaler/cloudprovider/cluster-autoscaler-autodiscover.yaml")

    def run_kube_bench(self):
        print("🔐 Running kube-bench scan...")
        self.run("kubectl run kube-bench --rm -i --tty --image=aquasec/kube-bench:latest -- /kube-bench", check=False)

    def enhance_cluster(self):
        print("✨ Enhancing cluster...")
        self.install_metrics_server()
        self.install_cluster_autoscaler()
        self.run_kube_bench()

    def full_upgrade_flow(self):
        self.backup_etcd()
        self.upgrade_kubeadm()
        self.plan_upgrade()
        self.apply_upgrade()
        self.upgrade_kubelet_and_kubectl()
        self.enhance_cluster()
        print("✅ Full upgrade and enhancement completed.")