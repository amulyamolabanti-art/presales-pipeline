using './main.bicep'

param environment = 'prod'

// Region: To confirm with IT Azure Platform team (defaults to eastus2)
param location = 'eastus2'

param workloadName = 'proposal-ai'
param instanceSuffix = '001'

param deployAiPlatformServices = true
param deploySql = true

// Corporate IP CIDR ranges permitted to access secured endpoints (OpenAI, AI Search, Storage, KV, Doc Intel)
// To be updated with corporate VPN / office egress CIDRs provided by IT SecOps
param corporateIpRanges = [
  '104.42.195.92/32'
  '40.76.54.131/32'
]

// Azure SQL Entra-only Administrator configuration
param sqlEntraAdminLogin = 'sg-proposal-ai-prod'
// When empty, automatically defaults to the User-Assigned Managed Identity during provisioning
param sqlEntraAdminObjectId = ''
param sqlEntraAdminPrincipalType = 'Group'

// Corporate firewall rules for Azure SQL Server
param sqlCorporateFirewallRules = [
  {
    name: 'CorporateVpnGateway-1'
    startIpAddress: '104.42.195.92'
    endIpAddress: '104.42.195.92'
  }
  {
    name: 'CorporateVpnGateway-2'
    startIpAddress: '40.76.54.131'
    endIpAddress: '40.76.54.131'
  }
]

param customTags = {
  Owner: 'Presales Operations'
  CostCenter: 'Presales-Production'
}
