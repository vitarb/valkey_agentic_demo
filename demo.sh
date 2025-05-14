#!/usr/bin/env bash
# demo.sh — launch / destroy a GPU EC2 instance running the Valkey agentic demo.
#   ./demo.sh up
#   ./demo.sh down
set -euo pipefail

# ───── configuration ────────────────────────────────────────────────────────
REGION=${AWS_DEFAULT_REGION:-us-east-1}
INSTANCE_TYPE=${INSTANCE_TYPE:-g5.2xlarge}
KEY_NAME=demo-key
SG_NAME=valkey-demo-sg
TAG_KEY=valkey-demo
TAG_VAL=agentic
MY_IP=$(curl -s https://checkip.amazonaws.com)/32      # refreshed each run
CMD=${1:-up}; [[ $CMD == up || $CMD == down ]] || { echo "Usage: $0 [up|down]"; exit 1; }

# ───── helpers ──────────────────────────────────────────────────────────────
latest_amzn2() {
  aws ec2 describe-images --owners amazon \
      --filters "Name=name,Values=amzn2-ami-hvm-*-gp2" "Name=architecture,Values=x86_64" \
      --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text --region "$REGION"
}

keypair_ensure() {
  local file_ok=0; [[ -f ${KEY_NAME}.pem ]] && file_ok=1
  local aws_ok; aws_ok=$(aws ec2 describe-key-pairs --key-names "$KEY_NAME" \
               --region "$REGION" --query 'KeyPairs[0].KeyName' --output text 2>/dev/null || true)
  if [[ $aws_ok == "$KEY_NAME" && $file_ok -eq 0 ]]; then
    echo "⚠  ${KEY_NAME}.pem missing locally – recreating key-pair"
    aws ec2 delete-key-pair --key-name "$KEY_NAME" --region "$REGION"
    aws_ok=""
  fi
  if [[ -z $aws_ok || $aws_ok == "None" ]]; then
    echo "⤵  creating key-pair $KEY_NAME"
    tmp=$(mktemp)
    aws ec2 create-key-pair --key-name "$KEY_NAME" --region "$REGION" \
        --query 'KeyMaterial' --output text > "$tmp"
    chmod 600 "$tmp"; mv -f "$tmp" "${KEY_NAME}.pem"
  fi
}

sg_ensure() {
  local id vpc
  id=$(aws ec2 describe-security-groups --filters Name=group-name,Values="$SG_NAME" \
        --query 'SecurityGroups[0].GroupId' --output text --region "$REGION" 2>/dev/null || true)

  if [[ -z $id || $id == "None" ]]; then
    echo "⤵  creating security group $SG_NAME"
    vpc=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true \
            --query 'Vpcs[0].VpcId' --output text --region "$REGION" 2>/dev/null)
    [[ -z $vpc || $vpc == "None" ]] && \
      vpc=$(aws ec2 describe-vpcs --query 'Vpcs[0].VpcId' --output text --region "$REGION")
    [[ -z $vpc || $vpc == "None" ]] && { echo "Fatal: no VPC"; exit 1; }

    id=$(aws ec2 create-security-group --group-name "$SG_NAME" \
          --description "Valkey demo SG" --vpc-id "$vpc" \
          --query 'GroupId' --output text --region "$REGION" 2>/dev/null || true)
    if [[ -z $id || $id == "None" ]]; then
      id=$(aws ec2 describe-security-groups --filters Name=group-name,Values="$SG_NAME" \
           --query 'SecurityGroups[0].GroupId' --output text --region "$REGION")
    fi
  fi
  [[ -z $id || $id == "None" ]] && { echo "Fatal: SG ID empty"; exit 1; }

  for port in 22 3000 9090; do
    aws ec2 authorize-security-group-ingress --group-id "$id" --region "$REGION" \
      --ip-permissions "IpProtocol=tcp,FromPort=$port,ToPort=$port,IpRanges=[{CidrIp=${MY_IP}}]" \
      2>/dev/null || true
  done
  echo "$id"
}

find_instance() {
  aws ec2 describe-instances \
    --filters "Name=instance-state-name,Values=pending,running,stopping,stopped" \
              "Name=tag:$TAG_KEY,Values=$TAG_VAL" \
    --query 'Reservations[].Instances[0].InstanceId' \
    --output text --region "$REGION" 2>/dev/null || true
}
public_ip() { aws ec2 describe-instances --instance-ids "$1" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' --output text --region "$REGION"; }

# ───── up ───────────────────────────────────────────────────────────────────
if [[ $CMD == up ]]; then
  IID=$(find_instance)
  if [[ -z $IID || $IID == "None" ]]; then
    keypair_ensure
    SG_ID=$(sg_ensure)
    AMI=$(latest_amzn2)

    echo "⤵  launching EC2 $INSTANCE_TYPE"
    IID=$(aws ec2 run-instances \
       --image-id "$AMI" --instance-type "$INSTANCE_TYPE" \
       --key-name "$KEY_NAME" --security-group-ids "$SG_ID" \
       --tag-specifications "ResourceType=instance,Tags=[{Key=$TAG_KEY,Value=$TAG_VAL}]" \
       --block-device-mappings "DeviceName=/dev/xvda,Ebs={VolumeSize=100}" \
       --user-data file://<(cat <<'EOF'
#!/bin/bash
exec > >(tee /var/log/user-data.log | logger -t user-data -s 2>/dev/console) 2>&1
set -eux
# --- packages: newer Python 3.11 + docker ------------------------------------------------
amazon-linux-extras enable python3.11 epel
yum -y install python3.11 python3.11-devel git docker
alternatives --set python3 /usr/bin/python3.11
python3 -m ensurepip --upgrade
python3 -m pip install --upgrade pip

systemctl enable --now docker
# Docker Compose v2 plugin
mkdir -p /usr/libexec/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
     -o /usr/libexec/docker/cli-plugins/docker-compose
chmod +x /usr/libexec/docker/cli-plugins/docker-compose
ln -s /usr/libexec/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose

# NVIDIA runtime for GPU
curl -fsSL https://nvidia.github.io/nvidia-docker/amzn2/nvidia-docker.repo \
 | tee /etc/yum.repos.d/nvidia-docker.repo
yum -y install nvidia-driver-latest-dkms nvidia-container-toolkit
systemctl restart docker
usermod -aG docker ec2-user

# --- demo setup (as ec2-user) ------------------------------------------------
sudo -u ec2-user bash <<'EOSU'
set -eux
cd ~
git clone --depth=1 https://github.com/vitarb/valkey_agentic_demo.git
cd valkey_agentic_demo
python3 -m pip install -r requirements.txt
python3 tools/make_cc_csv.py 50000 data/news_sample.csv
python3 tools/bootstrap_grafana.py
docker-compose pull 2>&1 | tee docker-compose.log
docker-compose up -d   2>&1 | tee -a docker-compose.log
EOSU
EOF
       ) --query 'Instances[0].InstanceId' --output text --region "$REGION")
    echo "⌛ waiting for status OK…"
    aws ec2 wait instance-status-ok --instance-ids "$IID" --region "$REGION"
  else
    echo "✔  reusing instance $IID"
    sg_ensure >/dev/null
  fi

  PUB=$(public_ip "$IID")
  cat <<EOF

🚀 Instance ready: $IID
SSH with port-forward:

  ssh -i ${KEY_NAME}.pem -L 3000:localhost:3000 -L 9090:localhost:9090 ec2-user@$PUB

Grafana   → http://localhost:3000  (admin / admin)
Prometheus→ http://localhost:9090

When finished:  $0 down
EOF
fi

# ───── down ─────────────────────────────────────────────────────────────────
if [[ $CMD == down ]]; then
  IID=$(find_instance)
  if [[ -z $IID || $IID == "None" ]]; then
    echo "No demo instance found."
    exit 0
  fi
  echo "🗑  terminating $IID"
  aws ec2 terminate-instances --instance-ids "$IID" --region "$REGION"
  aws ec2 wait instance-terminated --instance-ids "$IID" --region "$REGION"
  read -rp "Delete security-group and key-pair too? [y/N] " yn
  if [[ $yn == y* ]]; then
    SG_ID=$(sg_ensure)
    aws ec2 delete-security-group --group-id "$SG_ID" --region "$REGION" || true
    aws ec2 delete-key-pair --key-name "$KEY_NAME" --region "$REGION" || true
    rm -f "${KEY_NAME}.pem"
    echo "✓ cleanup done"
  fi
fi

