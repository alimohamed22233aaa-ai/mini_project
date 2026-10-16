output "web_server_public_ip" {
  description = "Public IP of the web-server instance"
  value       = aws_instance.depi.public_ip
}