export type DemoIdentity = 'platform-admin' | 'tenant-admin' | 'annotator' | 'reviewer'

export const DEMO_IDENTITIES: Array<{
  id: DemoIdentity
  label: string
  email: string
  description: string
  icon: string
}> = [
  {
    id: 'platform-admin',
    label: '平台管理员',
    email: 'Avery.Admin@example.com',
    description: '新增、查看和删除租户',
    icon: 'lucide:landmark',
  },
  {
    id: 'tenant-admin',
    label: '租户管理员',
    email: 'Avery.Tenant@example.com',
    description: '人员、问题视频复核和项目标签规则',
    icon: 'lucide:building-2',
  },
  {
    id: 'annotator',
    label: '标注员',
    email: 'Avery.Annotator@example.com',
    description: '播放视频、标注时间段并提交',
    icon: 'lucide:pen-line',
  },
  {
    id: 'reviewer',
    label: '审核员',
    email: 'Avery.Reviewer@example.com',
    description: '查看视频、审核通过或驳回',
    icon: 'lucide:scan-eye',
  },
]
