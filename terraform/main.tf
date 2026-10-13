# =====================================================================
# main.tf — Infrastructure as Code example: provision an isolated
# AWS EC2 lab VM that runs Docker + Jenkins for the VulnLab pipeline.
#
# TEACHING PURPOSE: this shows students the difference between
# "ClickOps" (manually creating a VM in the AWS Console) and
# Infrastructure as Code (declaring the VM in version-controlled code
# that can be reviewed, reused, and destroyed on demand).
#
# ⚠️ SECURITY: the security group below deliberately restricts access
# to YOUR_IP_CIDR only — never open 0.0.0.0/0 for a vulnerable app.
# =====================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  default = "ap-south-1" # Mumbai — closest region for India-based labs
}

variable "my_ip_cidr" {
  description = "Your IP in CIDR form, e.g. 103.21.45.10/32 — restrict lab access to just you/students"
  type        = string
}

variable "key_pair_name" {
  description = "Existing EC2 key pair name for SSH access"
  type        = string
}

# Isolated VPC + subnet so the lab never touches a shared/production network
resource "aws_vpc" "lab_vpc" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = { Name = "vulnlab-lab-vpc" }
}

resource "aws_subnet" "lab_subnet" {
  vpc_id                  = aws_vpc.lab_vpc.id
  cidr_block              = "10.42.1.0/24"
  map_public_ip_on_launch = true
  tags = { Name = "vulnlab-lab-subnet" }
}

resource "aws_internet_gateway" "lab_igw" {
  vpc_id = aws_vpc.lab_vpc.id
}

resource "aws_route_table" "lab_rt" {
  vpc_id = aws_vpc.lab_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.lab_igw.id
  }
}

resource "aws_route_table_association" "lab_rta" {
  subnet_id      = aws_subnet.lab_subnet.id
  route_table_id = aws_route_table.lab_rt.id
}

# Security Group: ONLY your IP, ONLY the ports needed (Jenkins 8080, app 5000, SSH 22)
resource "aws_security_group" "lab_sg" {
  name   = "vulnlab-lab-sg"
  vpc_id = aws_vpc.lab_vpc.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }
  ingress {
    description = "Jenkins UI"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }
  ingress {
    description = "VulnLab app (students only, same lab network/classroom IP range)"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# EC2 instance — bootstraps Docker + Jenkins automatically via user_data
resource "aws_instance" "lab_host" {
  ami                    = "ami-0f58b397bc5c1f2e8" # Ubuntu 22.04 LTS, ap-south-1 — verify current AMI ID before use
  instance_type          = "t3.medium"
  subnet_id              = aws_subnet.lab_subnet.id
  vpc_security_group_ids = [aws_security_group.lab_sg.id]
  key_name                = var.key_pair_name

  user_data = <<-EOF
    #!/bin/bash
    apt-get update -y
    apt-get install -y docker.io docker-compose
    systemctl enable --now docker
    usermod -aG docker ubuntu
    docker volume create jenkins_home
    docker run -d --name jenkins -p 8080:8080 -p 50000:50000 \
      -v jenkins_home:/var/jenkins_home \
      -v /var/run/docker.sock:/var/run/docker.sock \
      jenkins/jenkins:lts
  EOF

  tags = { Name = "vulnlab-lab-host" }
}

output "lab_host_public_ip" {
  value = aws_instance.lab_host.public_ip
}

output "jenkins_url" {
  value = "http://${aws_instance.lab_host.public_ip}:8080"
}

output "app_url" {
  value = "http://${aws_instance.lab_host.public_ip}:5000"
}
