terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}


provider "aws" {
  region  = "us-east-1"
  profile = "aliprofile"
}

module "task1" {
  source      = "../modules/ec2"
  vpc_cidr    = var.vpc_cidr
  subnet_cidr = var.subnet_cidr

  instance_name = var.instance_name
  sg-name       = var.sg-name

} 