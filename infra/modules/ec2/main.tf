resource "aws_vpc" "main" {
  cidr_block       = var.vpc_cidr
  instance_tenancy = "default"

  tags = {
    Name = "vpc_task"
  }
}
resource "aws_subnet" "public" {
  
  vpc_id     = aws_vpc.main.id
  cidr_block = var.subnet_cidr
  availability_zone = "us-east-1a"
  tags = {
    Name = "publicsubnet"
  }
}
resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "main"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
}  
resource "aws_route_table_association" "public" {
 
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "server" {
  name   = var.sg-name
  vpc_id = aws_vpc.main.id
  description = "security group of web-server"
  
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }

ingress {
    description = "port of app"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }
ingress {
    description = "port of app"
    from_port   = 9000
    to_port     = 9000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
    

  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}





data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] 

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "depi" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = "c7i-flex.large"
  subnet_id                   = aws_subnet.public.id
  key_name                    = "depi-key"
  associate_public_ip_address = true
  vpc_security_group_ids = [aws_security_group.server.id]
 root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }
user_data_replace_on_change = true
user_data = <<-EOT
    #!/bin/bash


    mkdir sonar-lab
    cd sonar-lab

    cat > docker-compose.yml <<'EOF'
    services:
      db:
        image: postgres:16
        restart: unless-stopped
        environment:
          POSTGRES_USER: sonar
          POSTGRES_PASSWORD: $${SONAR_DB_PASSWORD}
          POSTGRES_DB: sonar
        volumes: ["db_data:/var/lib/postgresql/data"]
      sonarqube:
        image: sonarqube:community
        restart: unless-stopped
        ports: ["9000:9000"]
        environment:
          SONAR_JDBC_URL: jdbc:postgresql://db:5432/sonar
          SONAR_JDBC_USERNAME: sonar
          SONAR_JDBC_PASSWORD: $${SONAR_DB_PASSWORD}
    volumes:
      db_data:
    EOF

    echo "SONAR_DB_PASSWORD=ali123" > .env

  EOT
  tags = {
    Name = var.instance_name
}
}