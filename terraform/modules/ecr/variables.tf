variable "repository_names" {
  description = "List of ECR repository names to create"
  type        = list(string)
}

variable "keep_image_count" {
  description = "Number of most recent images to keep per repository"
  type        = number
  default     = 10
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
