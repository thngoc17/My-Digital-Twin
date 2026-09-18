// Deploy ở SUBSCRIPTION SCOPE vì file này phải tự tạo ra Resource Group,
// nên không thể chạy ở resource-group scope (RG chưa tồn tại lúc bắt đầu).
targetScope = 'subscription'

@description('Vùng Azure để triển khai toàn bộ tài nguyên')
param location string = 'eastasia'

@description('Tên Resource Group sẽ được tạo mới. Nên set qua GitHub repo Variable "RESOURCE_GROUP" — dùng chung bởi infra.yml và deploy.yml — thay vì hard-code riêng ở từng nơi.')
param resourceGroupName string = 'digital-twin-rg'

@description('Tên Azure ML Workspace. Nên set qua GitHub repo Variable "WORKSPACE" — dùng chung bởi infra.yml và deploy.yml.')
param workspaceName string = 'qwen-twin-workspace'

@description('Tên Azure Container Registry. Để trống để Bicep tự sinh tên duy nhất — không nên hard-code, vì đây là tài nguyên do IaC tạo ra, không phải do người chọn trước.')
param acrName string = ''

@description('Tên Azure Key Vault — mặc định khớp với tên đang hardcode trong test/stress-test.py và test/chaos-test.py')
param keyVaultName string = 'qwen-rag-vault'

@description('Object ID của Service Principal dùng trong secrets.AZURE_CREDENTIALS (không phải Client/App ID)')
param githubActionsPrincipalId string

@description('Bật/tắt việc tự cấp role Contributor cho SP CI/CD (xem ghi chú quyền hạn trong modules/mlops-resources.bicep)')
param assignContributorRole bool = true

// Tên ACR là *output* của hạ tầng, không phải input do người tự nghĩ ra: nếu không truyền acrName,
// tự sinh một tên duy nhất, tái lập được (deterministic theo subscription + tên RG) — không hề hard-code.
var effectiveAcrName = empty(acrName) ? toLower('acr${uniqueString(subscription().id, resourceGroupName)}') : acrName

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
}

module mlopsResources 'modules/mlops-resources.bicep' = {
  name: 'mlopsResourcesDeployment'
  scope: resourceGroup(rg.name)
  params: {
    location: location
    workspaceName: workspaceName
    acrName: effectiveAcrName
    keyVaultName: keyVaultName
    githubActionsPrincipalId: githubActionsPrincipalId
    assignContributorRole: assignContributorRole
  }
}

output resourceGroupName string = rg.name
output workspaceName string = mlopsResources.outputs.workspaceName
output acrName string = effectiveAcrName
output acrLoginServer string = mlopsResources.outputs.acrLoginServer
output keyVaultUri string = mlopsResources.outputs.keyVaultUri
