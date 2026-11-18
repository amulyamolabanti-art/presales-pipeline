@description('The name of the Storage Account.')
param name string

@description('Target Azure region for the resource.')
param location string = resourceGroup().location

@description('Resource tags to apply.')
param tags object = {}

@description('The Storage Account SKU.')
@allowed([
  'Standard_LRS'
  'Standard_GRS'
  'Standard_RAGRS'
  'Standard_ZRS'
  'Premium_LRS'
])
param skuName string = 'Standard_LRS'

@description('Array of corporate IP addresses or CIDR blocks allowed to access the service.')
param corporateIpRanges array = []

@description('List of blob container names to create.')
param containerNames array = [
  'app-package'
  'rfp-documents'
]

var storageIpRules = [for ip in corporateIpRanges: {
  value: ip
  action: 'Allow'
}]

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    accessTier: 'Hot'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: empty(corporateIpRanges) ? 'Allow' : 'Deny'
      ipRules: storageIpRules
    }
    encryption: {
      services: {
        blob: {
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [for containerName in containerNames: {
  parent: blobService
  name: containerName
  properties: {
    publicAccess: 'None'
  }
}]

@description('The resource ID of the Storage Account.')
output id string = storageAccount.id

@description('The name of the Storage Account.')
output name string = storageAccount.name

@description('The primary endpoints object of the Storage Account.')
output primaryEndpoints object = storageAccount.properties.primaryEndpoints

@description('The primary blob endpoint URL.')
output blobEndpoint string = storageAccount.properties.primaryEndpoints.blob
