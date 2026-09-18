// Module này chạy trong scope của Resource Group (được gọi từ infra/main.bicep ở subscription scope)

@description('Vùng Azure')
param location string

@description('Tên Azure ML Workspace')
param workspaceName string

@description('Tên Azure Container Registry (chỉ chữ thường/số, 5-50 ký tự, phải unique toàn cầu trong Azure)')
param acrName string

@description('Tên Azure Key Vault (đang khớp với test/stress-test.py và test/chaos-test.py)')
param keyVaultName string

@description('Object ID (không phải Client ID) của Service Principal dùng trong secrets.AZURE_CREDENTIALS của GitHub Actions')
param githubActionsPrincipalId string

@description('Có tạo role assignment Contributor cho SP CI/CD hay không. Đặt false nếu SP chạy Bicep không có quyền User Access Administrator/Owner ở subscription.')
param assignContributorRole bool = true

var storageAccountName = toLower('st${uniqueString(resourceGroup().id)}')
var appInsightsName = '${workspaceName}-ai'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

// RBAC-based Key Vault (không dùng access policy kiểu cũ)
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enabledForTemplateDeployment: true
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
  }
}

// SKU phải >= Standard: Azure ML không cho gắn ACR tier Basic vào workspace
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    adminUserEnabled: false // dùng RBAC (AAD) qua `az acr login`, không cần admin user
  }
}

resource mlWorkspace 'Microsoft.MachineLearningServices/workspaces@2023-04-01' = {
  name: workspaceName
  location: location
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: workspaceName
    storageAccount: storageAccount.id
    keyVault: keyVault.id
    applicationInsights: appInsights.id
    containerRegistry: acr.id
  }
}

// Cấp quyền cho managed identity của Workspace được đọc/ghi secret trong Key Vault (RBAC)
resource kvRoleForWorkspace 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, mlWorkspace.id, 'KeyVaultSecretsOfficer')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7') // Key Vault Secrets Officer
    principalId: mlWorkspace.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Cấp quyền Contributor cho SP của GitHub Actions trên toàn bộ Resource Group
// ⚠️ Yêu cầu: SP chạy deployment Bicep này phải có "User Access Administrator" hoặc "Owner"
//    ở cấp subscription, nếu không resource này sẽ lỗi vì Contributor không được phép tạo role assignment.
resource ciCdContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (assignContributorRole) {
  name: guid(resourceGroup().id, githubActionsPrincipalId, 'Contributor')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c') // Contributor
    principalId: githubActionsPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output workspaceName string = mlWorkspace.name
output acrLoginServer string = acr.properties.loginServer
output keyVaultUri string = keyVault.properties.vaultUri
output storageAccountName string = storageAccount.name
output appInsightsName string = appInsights.name
