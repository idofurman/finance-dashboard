resource "helm_release" "argocd" {
  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  namespace        = "argocd"
  create_namespace = true

  set {
    name  = "server.service.type"
    value = "ClusterIP"
  }

  depends_on = [module.eks]
}

resource "null_resource" "argocd_application" {
  depends_on = [helm_release.argocd]

  triggers = {
    argocd_release = helm_release.argocd.metadata[0].revision
  }

  provisioner "local-exec" {
    command = <<-EOT
      aws eks update-kubeconfig --name ${module.eks.cluster_name} --region us-east-1
      kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=180s
      kubectl apply -f ${path.root}/../argocd/application.yml
    EOT
  }
}
