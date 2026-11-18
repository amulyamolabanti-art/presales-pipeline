@description('The name of the Document Intelligence service.')
param name string

@description('Target Azure region for the resource.')
param location string = resourceGroup().location

@description('Resource tags to apply.')
param tags object = {}

@description('SKU for the Document Intelligence account.')
@allowed([
  'F0'
  'S0'
])
param skuName string = 'S0'

@description('Array of corporate IP addresses or CIDR blocks allowed to access the service.')
param corporateIpRanges array = []

var diIpRules = [for ip in corporateIpRanges: {
  value: ip
}]

resource documentIntelligence 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  tags: tags
  kind: 'FormRecognizer'
  sku: {
    name: skuName
  }
  properties: {
    customSubDomainName: name
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: empty(corporateIpRanges) ? 'Allow' : 'Deny'
      ipRules: diIpRules
    }
  }
}

@description('The resource ID of the Document Intelligence account.')
output id string = documentIntelligence.id

@description('The name of the Document Intelligence account.')
output name string = documentIntelligence.name

@description('The HTTPS endpoint of the Document Intelligence service.')
output endpoint string = documentIntelligence.properties.endpoint
