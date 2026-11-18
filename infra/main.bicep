targetScope = 'resourceGroup'

@description('The deployment environment (dev, prod).')
@allowed([
  'dev'
  'prod'
])
param environment string = 'dev'

@description('Target Azure region for all resources (to confirm with IT Azure Platform team; defaults to resource group location).')
param location string = resourceGroup().location

@description('The short workload/project name used for naming conventions.')
@minLength(2)
@maxLength(15)
param workloadName string = 'proposal-ai'

@description('Unique suffix or instance sequence for resources requiring globally unique names.')
@minLength(3)
@maxLength(6)
param instanceSuffix string = '001'

@description('Deploy AI platform services (OpenAI, AI Search, Document Intelligence).')
param deployAiPlatformServices bool = true

@description('Deploy Azure SQL Database (serverless, Entra-only auth).')
param deploySql bool = true

@description('SKU for Azure AI Search (GA).')
param searchServiceSku string = environment == 'prod' ? 'standard' : 'basic'

@description('Array of corporate IP addresses or CIDR blocks allowed to access secured services.')
param corporateIpRanges array = []

@description('Entra ID administrator login for Azure SQL.')
param sqlEntraAdminLogin string = 'sg-proposal-ai-${environment}'

@description('Entra ID administrator object ID (principal ID / SID) for Azure SQL. If empty, falls back to the Managed Identity.')
param sqlEntraAdminObjectId string = ''

@description('Entra ID administrator principal type for Azure SQL.')
@allowed([
  'Group'
  'User'
  'Application'
])
param sqlEntraAdminPrincipalType string = 'Group'

@description('Corporate firewall rules for Azure SQL logical server: [{ name: string, startIpAddress: string, endIpAddress: string }].')
param sqlCorporateFirewallRules array = []

@description('Custom tags to merge with standard tags.')
param customTags object = {}

// ==============================================================================
// Naming Convention (Azure Cloud Adoption Framework compliant)
// Storage name: bounded to max 24 chars, guarantees suffix is never mangled
// ==============================================================================
var cleanWorkload = take(replace(replace(workloadName, '-', ''), 'ai', ''), 8)
var cleanLocation = toLower(location)
var storageBase = take('st${cleanWorkload}${environment}${cleanLocation}', 18)
var storageAccountName = '${storageBase}${instanceSuffix}'

var names = {
  managedIdentity: 'id-${workloadName}-${environment}-${location}'
  logAnalytics: 'log-${workloadName}-${environment}-${location}'
  appInsights: 'appi-${workloadName}-${environment}-${location}'
  keyVault: take('kv-${workloadName}-${environment}-${instanceSuffix}', 24)
  storageAccount: storageAccountName
  functionPlan: 'plan-${workloadName}-${environment}-${location}'
  functionApp: 'func-${workloadName}-${environment}-${location}'
  botService: 'bot-${workloadName}-${environment}-${location}'
  openAi: 'oai-${workloadName}-${environment}-${location}'
  aiSearch: 'srch-${workloadName}-${environment}-${location}'
  documentIntelligence: 'di-${workloadName}-${environment}-${location}'
  sqlServer: take('sql-${workloadName}-${environment}-${cleanLocation}-${instanceSuffix}', 63)
  sqlDatabase: 'sqldb-${workloadName}-${environment}'
}

// Standard tagging convention
var standardTags = {
  Environment: environment
  Project: 'Proposal AI'
  Workload: 'AI Proposal Assistant'
  ManagedBy: 'Bicep'
}
var combinedTags = union(standardTags, customTags)

// ==============================================================================
// 1. User Assigned Managed Identity (Passwordless / Keyless Architecture)
// ==============================================================================
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: names.managedIdentity
  location: location
  tags: combinedTags
}

// Fallback logic for SQL admin: uses provided ObjectID or falls back to Managed Identity
var effectiveSqlAdminId = !empty(sqlEntraAdminObjectId) ? sqlEntraAdminObjectId : managedIdentity.properties.principalId
var effectiveSqlAdminLogin = !empty(sqlEntraAdminObjectId) ? sqlEntraAdminLogin : names.managedIdentity
var effectiveSqlAdminType = !empty(sqlEntraAdminObjectId) ? sqlEntraAdminPrincipalType : 'Application'

// ==============================================================================
// 2. Monitoring & Observability (Log Analytics + App Insights)
// ==============================================================================
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: names.logAnalytics
  location: location
  tags: combinedTags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: environment == 'prod' ? 90 : 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: names.appInsights
  location: location
  tags: combinedTags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// ==============================================================================
// 3. Modular Storage & Key Vault (Key-Based Auth Disabled & Corporate IP Limited)
// ==============================================================================
module keyVault 'modules/keyvault.bicep' = {
  name: 'keyVaultDeployment'
  params: {
    name: names.keyVault
    location: location
    tags: combinedTags
    corporateIpRanges: corporateIpRanges
  }
}

module storageAccount 'modules/storage.bicep' = {
  name: 'storageAccountDeployment'
  params: {
    name: names.storageAccount
    location: location
    tags: combinedTags
    skuName: environment == 'prod' ? 'Standard_GRS' : 'Standard_LRS'
    corporateIpRanges: corporateIpRanges
    containerNames: [
      'app-package'
      'rfp-documents'
    ]
  }
}

// Scoped existing resource references for RBAC Role Assignments
resource storageAccountResource 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: names.storageAccount
  dependsOn: [
    storageAccount
  ]
}

var storageBlobDataOwnerRoleId = 'b7e6dc6d-f1e8-4753-8033-079c978541e8'
resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storageAccountResource
  name: guid(resourceGroup().id, names.storageAccount, managedIdentity.id, storageBlobDataOwnerRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataOwnerRoleId)
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource keyVaultResource 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: names.keyVault
  dependsOn: [
    keyVault
  ]
}

var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'
resource keyVaultRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: keyVaultResource
  name: guid(resourceGroup().id, names.keyVault, managedIdentity.id, keyVaultSecretsUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ==============================================================================
// 4. Compute: Functions Flex Consumption (Node 22) + Azure Bot Service
// ==============================================================================
resource functionPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: names.functionPlan
  location: location
  tags: combinedTags
  kind: 'functionapp'
  sku: {
    name: 'FC1'
    tier: 'FlexConsumption'
  }
  properties: {
    reserved: true
  }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: names.functionApp
  location: location
  tags: combinedTags
  kind: 'functionapp,linux'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    serverFarmId: functionPlan.id
    httpsOnly: true
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${storageAccount.outputs.blobEndpoint}app-package'
          authentication: {
            type: 'UserAssignedIdentity'
            userAssignedIdentityResourceId: managedIdentity.id
          }
        }
      }
      scaleAndConcurrency: {
        maximumInstanceCount: environment == 'prod' ? 100 : 40
        instanceMemoryMB: 2048
      }
      runtime: {
        name: 'node'
        version: '22'
      }
    }
    siteConfig: {
      appSettings: [
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'AZURE_CLIENT_ID'
          value: managedIdentity.properties.clientId
        }
        {
          name: 'KEY_VAULT_URI'
          value: keyVault.outputs.vaultUri
        }
        {
          name: 'STORAGE_ACCOUNT_NAME'
          value: storageAccount.outputs.name
        }
        {
          name: 'ENVIRONMENT'
          value: environment
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: deployAiPlatformServices ? (openAi.?outputs.endpoint ?? '') : ''
        }
        {
          name: 'AZURE_SEARCH_ENDPOINT'
          value: deployAiPlatformServices ? (aiSearch.?outputs.endpoint ?? '') : ''
        }
        {
          name: 'DOCUMENT_INTELLIGENCE_ENDPOINT'
          value: deployAiPlatformServices ? (documentIntelligence.?outputs.endpoint ?? '') : ''
        }
        {
          name: 'AZURE_SQL_SERVER'
          value: deploySql ? (sql.?outputs.fullyQualifiedDomainName ?? '') : ''
        }
        {
          name: 'AZURE_SQL_DATABASE'
          value: deploySql ? (sql.?outputs.databaseName ?? '') : ''
        }
      ]
    }
  }
  dependsOn: [
    storageRoleAssignment
  ]
}

// Azure Bot Service Registration connected to Managed Identity
resource botService 'Microsoft.BotService/botServices@2022-09-15' = {
  name: names.botService
  location: 'global'
  tags: combinedTags
  kind: 'azurebot'
  sku: {
    name: environment == 'prod' ? 'S1' : 'F0'
  }
  properties: {
    displayName: 'Proposal AI Assistant'
    endpoint: 'https://${functionApp.properties.defaultHostName}/api/messages'
    msaAppType: 'UserAssignedMSI'
    msaAppId: managedIdentity.properties.clientId
    msaAppTenantId: subscription().tenantId
    msaAppMSIResourceId: managedIdentity.id
  }
}

resource botChannelTeams 'Microsoft.BotService/botServices/channels@2022-09-15' = {
  parent: botService
  name: 'MsTeamsChannel'
  location: 'global'
  properties: {
    channelName: 'MsTeamsChannel'
    properties: {
      isEnabled: true
    }
  }
}

// ==============================================================================
// 5. Modular AI Platform Services (OpenAI, AI Search, Document Intelligence)
// ==============================================================================
module openAi 'modules/openai.bicep' = if (deployAiPlatformServices) {
  name: 'openAiDeployment'
  params: {
    name: names.openAi
    location: location
    tags: combinedTags
    corporateIpRanges: corporateIpRanges
  }
}

module aiSearch 'modules/search.bicep' = if (deployAiPlatformServices) {
  name: 'aiSearchDeployment'
  params: {
    name: names.aiSearch
    location: location
    tags: combinedTags
    skuName: searchServiceSku
    corporateIpRanges: corporateIpRanges
  }
}

module documentIntelligence 'modules/document-intelligence.bicep' = if (deployAiPlatformServices) {
  name: 'documentIntelligenceDeployment'
  params: {
    name: names.documentIntelligence
    location: location
    tags: combinedTags
    corporateIpRanges: corporateIpRanges
  }
}

// Scoped existing resource references & RBAC for AI Platform
resource openAiAccountResource 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = if (deployAiPlatformServices) {
  name: names.openAi
  dependsOn: [
    openAi
  ]
}

var cognitiveServicesOpenAiUserRoleId = '5e0dc2a8-83de-43f0-88d4-e66f5c664882'
resource openAiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (deployAiPlatformServices) {
  scope: openAiAccountResource
  name: guid(resourceGroup().id, names.openAi, managedIdentity.id, cognitiveServicesOpenAiUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAiUserRoleId)
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource searchServiceResource 'Microsoft.Search/searchServices@2023-11-01' existing = if (deployAiPlatformServices) {
  name: names.aiSearch
  dependsOn: [
    aiSearch
  ]
}

var searchIndexDataContributorRoleId = '8ebe5a00-a779-4933-a329-9fdd56b6632c'
resource searchRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (deployAiPlatformServices) {
  scope: searchServiceResource
  name: guid(resourceGroup().id, names.aiSearch, managedIdentity.id, searchIndexDataContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataContributorRoleId)
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource docIntelResource 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = if (deployAiPlatformServices) {
  name: names.documentIntelligence
  dependsOn: [
    documentIntelligence
  ]
}

var cognitiveServicesUserRoleId = 'a97b65f3-24c7-4388-baec-2e87135dc908'
resource docIntelRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (deployAiPlatformServices) {
  scope: docIntelResource
  name: guid(resourceGroup().id, names.documentIntelligence, managedIdentity.id, cognitiveServicesUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRoleId)
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ==============================================================================
// 6. Modular Azure SQL (Serverless, Entra-Only Authentication)
// ==============================================================================
module sql 'modules/sql.bicep' = if (deploySql) {
  name: 'sqlDeployment'
  params: {
    serverName: names.sqlServer
    databaseName: names.sqlDatabase
    location: location
    tags: combinedTags
    entraAdminLogin: effectiveSqlAdminLogin
    entraAdminObjectId: effectiveSqlAdminId
    entraAdminPrincipalType: effectiveSqlAdminType
    corporateFirewallRules: sqlCorporateFirewallRules
    allowAzureServices: true
  }
}

// ==============================================================================
// Outputs for downstream deployment workflows and application configuration
// ==============================================================================
output resourceGroupName string = resourceGroup().name
output managedIdentityId string = managedIdentity.id
output managedIdentityClientId string = managedIdentity.properties.clientId
output managedIdentityPrincipalId string = managedIdentity.properties.principalId
output functionAppName string = functionApp.name
output functionAppEndpoint string = 'https://${functionApp.properties.defaultHostName}'
output botServiceName string = botService.name
output keyVaultName string = keyVault.outputs.name
output keyVaultUri string = keyVault.outputs.vaultUri
output storageAccountName string = storageAccount.outputs.name
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output openAiEndpoint string = deployAiPlatformServices ? (openAi.?outputs.endpoint ?? '') : ''
output aiSearchEndpoint string = deployAiPlatformServices ? (aiSearch.?outputs.endpoint ?? '') : ''
output documentIntelligenceEndpoint string = deployAiPlatformServices ? (documentIntelligence.?outputs.endpoint ?? '') : ''
output sqlServerName string = deploySql ? (sql.?outputs.serverName ?? '') : ''
output sqlServerFqdn string = deploySql ? (sql.?outputs.fullyQualifiedDomainName ?? '') : ''
output sqlDatabaseName string = deploySql ? (sql.?outputs.databaseName ?? '') : ''
