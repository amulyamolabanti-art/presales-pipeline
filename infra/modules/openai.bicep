@description('The name of the Azure OpenAI service.')
param name string

@description('Target Azure region for the resource.')
param location string = resourceGroup().location

@description('Resource tags to apply.')
param tags object = {}

@description('SKU for the OpenAI account.')
@allowed([
  'S0'
])
param skuName string = 'S0'

@description('Array of corporate IP addresses or CIDR blocks allowed to access the service.')
param corporateIpRanges array = []

resource openAi 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: skuName
  }
  properties: {
    customSubDomainName: name
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: empty(corporateIpRanges) ? 'Allow' : 'Deny'
      bypass: 'AzureServices'
      ipRules: [for ip in corporateIpRanges: {
        value: ip
      }]
    }
  }
}

@description('The resource ID of the OpenAI account.')
output id string = openAi.id

@description('The name of the OpenAI account.')
output name string = openAi.name

@description('The HTTPS endpoint of the OpenAI service.')
output endpoint string = openAi.properties.endpoint
