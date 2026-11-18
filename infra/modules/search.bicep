@description('The name of the Azure AI Search service.')
param name string

@description('Target Azure region for the resource.')
param location string = resourceGroup().location

@description('Resource tags to apply.')
param tags object = {}

@description('The pricing tier (SKU) of the Search service.')
@allowed([
  'free'
  'basic'
  'standard'
  'standard2'
  'standard3'
  'storage_optimized_l1'
  'storage_optimized_l2'
])
param skuName string = 'basic'

@description('The number of replicas.')
param replicaCount int = 1

@description('The number of partitions.')
param partitionCount int = 1

@description('Array of corporate IP addresses or CIDR blocks allowed to access the service.')
param corporateIpRanges array = []

var searchIpRules = [for ip in corporateIpRanges: {
  value: ip
}]

resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  properties: {
    replicaCount: replicaCount
    partitionCount: partitionCount
    hostingMode: 'default'
    disableLocalAuth: true
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    publicNetworkAccess: 'enabled'
    networkRuleSet: empty(corporateIpRanges) ? null : {
      ipRules: searchIpRules
    }
  }
}

@description('The resource ID of the Search service.')
output id string = searchService.id

@description('The name of the Search service.')
output name string = searchService.name

@description('The endpoint URL of the Search service.')
output endpoint string = 'https://${searchService.name}.search.windows.net'
