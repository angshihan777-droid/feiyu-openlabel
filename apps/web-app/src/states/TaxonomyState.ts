import { reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { openlabelApi } from '@/api'
import { jobConfig } from './job-config'

export const taxonomyState = reactive({
  ontologyClassNames: null as string[] | null,
  classNameToClass: undefined as Map<string, any> | undefined,
  ontology: null as any,
  taxonomyInfo: {
    meta: null as any,
    ontologies: [] as any[],
  },
  seqAnnoSchema: undefined as { schema: any } | undefined,
})

function indexClasses(node: any, target: Map<string, any>) {
  target.set(node.name, node)
  for (const child of node.children ?? []) indexClasses(child, target)
}

function parseSpec(data: any) {
  const classes = data?.openlabel?.classes ?? []
  if (classes.length === 0) throw new Error('标注规范没有 classes')
  taxonomyState.taxonomyInfo.meta = data.openlabel.meta
  taxonomyState.taxonomyInfo.ontologies = data.openlabel.ontologies ?? []
  taxonomyState.ontology = classes[0].children
  const classMap = new Map<string, any>()
  indexClasses(classes[0], classMap)
  taxonomyState.classNameToClass = classMap
  taxonomyState.seqAnnoSchema = classes[1] ? { schema: classes[1] } : undefined
}

export async function getOntologyClassNames() {
  const response = await openlabelApi.classes()
  taxonomyState.ontologyClassNames = response.data ?? response
}

export async function loadSpec() {
  try {
    const response = await openlabelApi.query({
      taxonomy: jobConfig.taxonomy,
      domain: jobConfig.taxonomy.domain,
    })
    const rows = response.data ?? response
    if (Array.isArray(rows) && rows.length === 1) {
      parseSpec(rows[0])
    } else {
      ElMessage.error('获取视频标注规范失败')
    }
  } catch {
    ElMessage.error('获取视频标注规范失败')
  }
}

watch(
  () => jobConfig.taxonomy,
  () => loadSpec(),
)
