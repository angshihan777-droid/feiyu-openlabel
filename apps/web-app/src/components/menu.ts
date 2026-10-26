import { type Menus } from '@/types/menu';

export const menuData: Menus[] = [
    {
        id: 'platform-admin',
        title: '平台租户管理',
        icon: 'material-symbols:domain-add',
        index: '/platform-admin',
        role: 'platform-admin',
    },
    {
        id: 'tenant-admin',
        title: '租户管理工作台',
        icon: 'material-symbols:business-center',
        index: '/tenant-admin',
        role: 'admin',
    },
    {
        id: '2v2',
        title: '我的标注任务',
        icon: 'material-symbols:draw-outline',
        index: '/my-tasks',
        role: 'annotator',
    },
    {
        id: '2v3',
        title: '我的审核任务',
        icon: 'material-symbols:fact-check-outline',
        index: '/my-reviews',
        role: 'reviewer',
    },
    {
        id: '4',
        title: '标注管理',
        index: '4',
        icon: 'material-symbols:description-outline',
        children: [
            {
                // Stage 9.6: workflow 驱动的批次管理
                id: '46',
                pid: '1',
                index: '/batches',
                title: '批次管理',
                role: 'admin',
            },
        ]
    },
    {
        id: '1',
        title: '系统设置',
        index: '2',
        icon: 'material-symbols:settings-outline',
        children: [
            {
                id: '11',
                pid: '1',
                index: '/user-info',
                title: '我的信息',
            },
        ],
    },
    
];
