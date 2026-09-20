// Module này chạy trong scope của Resource Group (RG đã tồn tại từ trước — xem infra/bootstrap.sh).
// Toàn bộ resource ở đây chỉ cần quyền Contributor trên RG. KHÔNG có resource nào loại
// Microsoft.Authorization/roleAssignments — vì Contributor không được phép tạo loại đó.

@description('Vùng Azure')
param location string

@description('Tên Azure ML Workspace')
param workspaceName string

@description('Tên Azure Container Registry. Để trống để tự sinh tên duy nhất, không hard-code.')
param acrName string = ''

@description('Tên Azure Key Vault (đang khớp với test/stress-test.py và test/chaos-test.py)')
param keyVaultName string

var effectiveAcrName = empty(acrName) ? toLower('acr${uniqueString(resourceGroup().id)}') : acrName
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

// Dùng access policy kiểu cổ điển (KHÔNG bật RBAC) một cách CÓ CHỦ ĐÍCH:
// việc set accessPolicies là một property write bình thường trên chính resource Key Vault
// (nằm trong quyền Contributor), khác với việc tạo Microsoft.Authorization/roleAssignments
// (đòi hỏi User Access Administrator/Owner). Đây là cách né việc cần quyền cao mà vẫn
// cấp được quyền đọc/ghi secret cho managed identity của Workspace.
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: false
    enabledForTemplateDeployment: true
    accessPolicies: []
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
  name: effectiveAcrName
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    adminUserEnabled: false // dùng AAD token (`az acr login`) nhờ Contributor, không cần admin user
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

// Child resource riêng (thay vì roleAssignment) để tránh vòng phụ thuộc:
// Key Vault cần tồn tại trước để Workspace tham chiếu tới, nhưng access policy
// lại cần principalId của Workspace — nên phải add SAU khi cả hai đã tồn tại.
// Đây vẫn chỉ là property write trên Key Vault, không đụng tới Authorization RBAC.
resource kvAccessPolicyForWorkspace 'Microsoft.KeyVault/vaults/accessPolicies@2023-07-01' = {
  parent: keyVault
  name: 'add'
  properties: {
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: mlWorkspace.identity.principalId
        permissions: {
          secrets: [
            'get'
            'list'
            'set'
            'delete'
          ]
        }
      }
    ]
  }
}

output workspaceName string = mlWorkspace.name
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output keyVaultUri string = keyVault.properties.vaultUri
output storageAccountName string = storageAccount.name
output appInsightsName string = appInsights.name
