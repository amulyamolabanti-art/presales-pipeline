@description('The name of the Azure SQL logical server.')
param serverName string

@description('The name of the SQL database.')
param databaseName string = 'sqldb-proposal-ai'

@description('Target Azure region for the resource.')
param location string = resourceGroup().location

@description('Resource tags to apply.')
param tags object = {}

@description('The Entra ID (Azure AD) administrator login name.')
param entraAdminLogin string

@description('The Entra ID (Azure AD) administrator object ID (principal ID / SID).')
param entraAdminObjectId string

@description('The Entra ID (Azure AD) administrator principal type.')
@allowed([
  'Group'
  'User'
  'Application'
])
param entraAdminPrincipalType string = 'Group'

@description('List of corporate firewall IP rules: [{ name: string, startIpAddress: string, endIpAddress: string }].')
param corporateFirewallRules array = []

@description('Allow Azure services and resources to access this server (firewall rule 0.0.0.0).')
param allowAzureServices bool = true

@description('The SKU name for Serverless Azure SQL Database.')
param databaseSkuName string = 'GP_S_Gen5_1'

@description('The maximum vCores for the serverless database.')
param databaseCapacity int = 1

@description('The minimum vCores for the serverless database.')
param databaseMinCapacity string = '0.5'

@description('Auto-pause delay in minutes for serverless compute (-1 to disable).')
param autoPauseDelayMinutes int = 60

@description('The maximum size of the database in bytes.')
param databaseMaxSizeBytes int = 34359738368 // 32 GB

resource sqlServer 'Microsoft.Sql/servers@2023-08-01-preview' = {
  name: serverName
  location: location
  tags: tags
  properties: {
    version: '12.0'
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    administrators: {
      administratorType: 'ActiveDirectory'
      principalType: entraAdminPrincipalType
      login: entraAdminLogin
      sid: entraAdminObjectId
      tenantId: subscription().tenantId
      azureADOnlyAuthentication: true
    }
  }
}

// Optional firewall rule to permit internal Azure services (Function App, Bot, etc.)
resource azureServicesRule 'Microsoft.Sql/servers/firewallRules@2023-08-01-preview' = if (allowAzureServices) {
  parent: sqlServer
  name: 'AllowAllWindowsAzureIps'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Corporate IP firewall rules
resource corporateRules 'Microsoft.Sql/servers/firewallRules@2023-08-01-preview' = [for rule in corporateFirewallRules: {
  parent: sqlServer
  name: rule.name
  properties: {
    startIpAddress: rule.startIpAddress
    endIpAddress: rule.endIpAddress
  }
}]

resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-08-01-preview' = {
  parent: sqlServer
  name: databaseName
  location: location
  tags: tags
  sku: {
    name: databaseSkuName
    tier: 'GeneralPurpose'
    family: 'Gen5'
    capacity: databaseCapacity
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: databaseMaxSizeBytes
    minCapacity: json(databaseMinCapacity)
    autoPauseDelay: autoPauseDelayMinutes
  }
}

@description('The resource ID of the SQL Server.')
output serverId string = sqlServer.id

@description('The fully qualified domain name of the SQL Server.')
output fullyQualifiedDomainName string = sqlServer.properties.fullyQualifiedDomainName

@description('The name of the SQL Server.')
output serverName string = sqlServer.name

@description('The resource ID of the SQL Database.')
output databaseId string = sqlDatabase.id

@description('The name of the SQL Database.')
output databaseName string = sqlDatabase.name
