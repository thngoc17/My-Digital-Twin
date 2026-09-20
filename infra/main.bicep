// Deploy ở RESOURCE GROUP SCOPE (mặc định của Bicep) — KHÔNG phải subscription scope.
// Resource Group phải đã tồn tại từ trước (xem infra/bootstrap.sh, chạy 1 lần bởi người có quyền cao).
// Nhờ vậy, Service Principal dùng trong GitHub Actions (secrets.AZURE_CREDENTIALS) chỉ cần
// quyền Contributor trên đúng 1 Resource Group này — không cần Owner/Contributor ở subscription.

@description('Vùng Azure')
param location string = 'eastasia'

@description('Tên Azure ML Workspace. Nên set qua GitHub repo Variable "WORKSPACE" — dùng chung bởi infra.yml và deploy.yml.')
param workspaceName string = 'qwen-twin-workspace'

@description('Tên Azure Container Registry. Để trống để Bicep tự sinh tên duy nhất — không nên hard-code.')
param acrName string = ''

@description('Tên Azure Key Vault — mặc định khớp với tên đang hardcode trong test/stress-test.py và test/chaos-test.py')
param keyVaultName string = 'qwen-twin-vault'

module mlopsResources 'modules/mlops-resources.bicep' = {
  name: 'mlopsResourcesDeployment'
  params: {
    location: location
    workspaceName: workspaceName
    acrName: acrName
    keyVaultName: keyVaultName
  }
}

output workspaceName string = mlopsResources.outputs.workspaceName
output acrName string = mlopsResources.outputs.acrName
output acrLoginServer string = mlopsResources.outputs.acrLoginServer
output keyVaultUri string = mlopsResources.outputs.keyVaultUri
