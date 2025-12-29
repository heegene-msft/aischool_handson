targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('환경 이름 (리소스 이름에 사용)')
param environmentName string

@minLength(1)
@description('리소스 배포 위치')
@allowed([
  'eastus'
  'eastus2'
  'westus'
  'westus2'
  'koreacentral'
  'japaneast'
  'southeastasia'
])
param location string

@description('리소스 그룹 이름')
param resourceGroupName string = ''

// Microsoft Foundry 설정
@description('Azure AI Services 계정 이름')
param aiServicesName string = ''

@description('모델 배포 이름')
param modelDeploymentName string = 'gpt-4o-mini'

// Azure AI Search 설정
@description('Azure AI Search 서비스 이름')
param searchServiceName string = ''

@allowed(['basic', 'standard'])
param searchServiceSkuName string = 'basic'

@description('검색 인덱스 이름')
param searchIndexName string = 'gptkbindex'

// Container Apps 설정
@description('Container Apps 환경 이름')
param containerAppsEnvironmentName string = ''

@description('Container App 이름')
param containerAppName string = ''

@description('Container Registry 이름')
param containerRegistryName string = ''

// Log Analytics
@description('Log Analytics 워크스페이스 이름')
param logAnalyticsName string = ''

// 태그
param tags object = {}

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

// 리소스 이름 생성
var actualResourceGroupName = !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
var actualAiServicesName = !empty(aiServicesName) ? aiServicesName : '${abbrs.cognitiveServicesAccounts}${resourceToken}'
var actualSearchServiceName = !empty(searchServiceName) ? searchServiceName : '${abbrs.searchSearchServices}${resourceToken}'
var actualContainerAppsEnvironmentName = !empty(containerAppsEnvironmentName) ? containerAppsEnvironmentName : '${abbrs.appManagedEnvironments}${resourceToken}'
var actualContainerAppName = !empty(containerAppName) ? containerAppName : '${abbrs.appContainerApps}backend-${resourceToken}'
var actualContainerRegistryName = !empty(containerRegistryName) ? containerRegistryName : '${abbrs.containerRegistryRegistries}${resourceToken}'
var actualLogAnalyticsName = !empty(logAnalyticsName) ? logAnalyticsName : '${abbrs.operationalInsightsWorkspaces}${resourceToken}'

// 리소스 그룹
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: actualResourceGroupName
  location: location
  tags: tags
}

// Log Analytics 워크스페이스
module logAnalytics 'core/monitor/loganalytics.bicep' = {
  name: 'loganalytics'
  scope: rg
  params: {
    name: actualLogAnalyticsName
    location: location
    tags: tags
  }
}

// Azure AI Services (Cognitive Services)
module aiServices 'core/ai/cognitiveservices.bicep' = {
  name: 'aiservices'
  scope: rg
  params: {
    name: actualAiServicesName
    location: location
    tags: tags
    kind: 'AIServices'
    sku: {
      name: 'S0'
    }
    deployments: [
      {
        name: modelDeploymentName
        model: {
          format: 'OpenAI'
          name: 'gpt-4o-mini'
          version: '2024-07-18'
        }
        sku: {
          name: 'GlobalStandard'
          capacity: 30
        }
      }
    ]
  }
}

// Azure AI Search
module searchService 'core/search/search-services.bicep' = {
  name: 'searchservice'
  scope: rg
  params: {
    name: actualSearchServiceName
    location: location
    tags: tags
    sku: {
      name: searchServiceSkuName
    }
    semanticSearch: 'standard'
  }
}

// Container Registry
module containerRegistry 'core/host/container-registry.bicep' = {
  name: 'containerregistry'
  scope: rg
  params: {
    name: actualContainerRegistryName
    location: location
    tags: tags
  }
}

// Container Apps Environment
module containerAppsEnvironment 'core/host/container-apps-environment.bicep' = {
  name: 'containerapps-environment'
  scope: rg
  params: {
    name: actualContainerAppsEnvironmentName
    location: location
    tags: tags
    logAnalyticsWorkspaceName: logAnalytics.outputs.name
  }
}

// Container App (Backend)
module containerApp 'core/host/container-app.bicep' = {
  name: 'containerapp'
  scope: rg
  params: {
    name: actualContainerAppName
    location: location
    tags: union(tags, { 'azd-service-name': 'backend' })
    containerAppsEnvironmentName: containerAppsEnvironment.outputs.name
    containerRegistryName: containerRegistry.outputs.name
    env: [
      {
        name: 'AZURE_AI_PROJECT_ENDPOINT'
        value: aiServices.outputs.endpoint
      }
      {
        name: 'AZURE_AI_MODEL_DEPLOYMENT_NAME'
        value: modelDeploymentName
      }
      {
        name: 'AZURE_SEARCH_SERVICE_ENDPOINT'
        value: searchService.outputs.endpoint
      }
      {
        name: 'AZURE_SEARCH_INDEX_NAME'
        value: searchIndexName
      }
    ]
    targetPort: 50505
  }
}

// Role Assignments - AI Services Cognitive Services User
module aiServicesRoleAssignment 'core/security/role.bicep' = {
  name: 'aiservices-role'
  scope: rg
  params: {
    principalId: containerApp.outputs.identityPrincipalId
    roleDefinitionId: 'a97b65f3-24c7-4388-baec-2e87135dc908'
    principalType: 'ServicePrincipal'
  }
}

// Role Assignments - Search Index Data Reader
module searchRoleAssignment 'core/security/role.bicep' = {
  name: 'search-role'
  scope: rg
  params: {
    principalId: containerApp.outputs.identityPrincipalId
    roleDefinitionId: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_AI_SERVICES_NAME string = aiServices.outputs.name
output AZURE_AI_PROJECT_ENDPOINT string = aiServices.outputs.endpoint
output AZURE_AI_MODEL_DEPLOYMENT_NAME string = modelDeploymentName
output AZURE_SEARCH_SERVICE_NAME string = searchService.outputs.name
output AZURE_SEARCH_SERVICE_ENDPOINT string = searchService.outputs.endpoint
output AZURE_SEARCH_INDEX_NAME string = searchIndexName
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.outputs.loginServer
output SERVICE_BACKEND_URI string = containerApp.outputs.uri
