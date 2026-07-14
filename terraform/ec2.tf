# ============================================================
# SSH Key Pair — uses your local public key
# ============================================================
resource "aws_key_pair" "finance_key" {
  key_name   = "finance-dashboard-key"
  public_key = file("~/.ssh/id_ed25519.pub")
}

# ============================================================
# Security Group — firewall rules for the server
# ============================================================
resource "aws_security_group" "finance_sg" {
  name        = "finance-dashboard-sg"
  description = "Finance dashboard k3s server"

  ingress {
    description = "SSH — restrict to your own IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.admin_cidr_blocks
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "k3s API server — restrict to your own IP"
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = var.admin_cidr_blocks
  }

  ingress {
    description = "NodePort services"
    from_port   = 30000
    to_port     = 32767
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "finance-dashboard-sg"
  }
}

# ============================================================
# IAM Role — lets the EC2 instance pull images from ECR
# ============================================================
resource "aws_iam_role" "ec2_role" {
  name = "finance-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "finance-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# ============================================================
# Find latest Ubuntu 22.04 LTS AMI automatically
# ============================================================
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical (Ubuntu's official AWS account)

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ============================================================
# EC2 Instance — the server that runs k3s
# ============================================================
resource "aws_instance" "finance_server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t3.medium"
  key_name               = aws_key_pair.finance_key.key_name
  vpc_security_group_ids = [aws_security_group.finance_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  user_data = <<-EOF
    #!/bin/bash
    apt-get update -y
    apt-get install -y curl awscli

    # Install k3s
    curl -sfL https://get.k3s.io | sh -

    # Allow ubuntu user to use kubectl without sudo
    mkdir -p /home/ubuntu/.kube
    cp /etc/rancher/k3s/k3s.yaml /home/ubuntu/.kube/config
    chown ubuntu:ubuntu /home/ubuntu/.kube/config
    chmod 600 /home/ubuntu/.kube/config
    sed -i 's/127.0.0.1/localhost/g' /home/ubuntu/.kube/config

    # Install Helm
    curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
  EOF

  tags = {
    Name = "finance-dashboard-server"
  }
}

# ============================================================
# Elastic IP — a fixed public IP that never changes
# ============================================================
resource "aws_eip" "finance_ip" {
  instance = aws_instance.finance_server.id
  domain   = "vpc"

  tags = {
    Name = "finance-dashboard-ip"
  }
}

# ============================================================
# Outputs — printed after terraform apply
# ============================================================
output "server_ip" {
  value       = aws_eip.finance_ip.public_ip
  description = "Public IP of the finance dashboard server"
}

output "ssh_command" {
  value       = "ssh -i ~/.ssh/id_ed25519 ubuntu@${aws_eip.finance_ip.public_ip}"
  description = "SSH command to connect to the server"
}

output "app_url" {
  value       = "http://${aws_eip.finance_ip.public_ip}:30500"
  description = "URL to access the finance dashboard"
}
