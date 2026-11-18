@description('The name of the Key Vault (max 24 characters).')
@maxLength(24)
param name string

@description('Target Azure region for the resource.')
param location string = resourceGroup().location

@description('Resource tags to apply.')
param tags object = {}

@description('The SKU family and name for the Key Vault.')
param skuName string = 'standard'

@description('Array of corporate IP addresses or CIDR blocks allowed to access the service.')
param corporateIpRanges array = []

@description('Soft delete retention in days.')
param softDeleteRetentionInDays int = 7

var kvIpRules = [for ip in corporateIpRanges: {
  value: ip
}]

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: skuName
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: softDeleteRetentionInDays
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: empty(corporateIpRanges) ? 'Allow' : 'Deny'
      ipRules: kvIpRules
    }
  }
}

@description('The resource ID of the Key Vault.')
output id string = keyVault.id

@description('The name of the Key Vault.')
output name string = keyVault.name

@description('The URI of the Key Vault.')
output vaultUri string = keyVault.properties.vaultUri
