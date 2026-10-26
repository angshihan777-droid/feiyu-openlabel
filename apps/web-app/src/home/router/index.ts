import { createRouter, createWebHashHistory } from 'vue-router'
import Home from '../views/home.vue';
import { userAuth } from '@/states/UserState'
import { usePermission } from '@/states/usePermission'
import { roleLandingPath } from '../role-landing'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/403',
      name: 'ForbiddenAccess',
      component: () => import('../views/pages/403.vue')
    },
    {
      path: '/',
      name: 'Home',
      component: Home,
      redirect: () => roleLandingPath(userAuth.value.roles),
      children: [
        {
          path: '/about',
          name: 'about',
          meta: { title: '关于', requireAuth: false, closable: true },
          component: () => import('../views/AboutView.vue')
        },
        {
          path: '/my-tasks',
          name: 'my-tasks',
          meta: {
            title: '我的标注任务',
            requireAuth: true,
            roles: ['annotator'],
            closable: true,
          },
          component: () => import('../views/challenge/AnnotatorWorkspace.vue'),
        },
        {
          path: '/my-reviews',
          name: 'my-reviews',
          meta: {
            title: '我的审核任务',
            requireAuth: true,
            roles: ['reviewer'],
            closable: true,
          },
          component: () => import('../views/challenge/ReviewerWorkspace.vue'),
        },
        {
          path: '/annotate/:unitId',
          name: 'annotate-video',
          meta: {
            title: '视频标注',
            requireAuth: true,
            roles: ['annotator'],
            closable: true,
          },
          component: () => import('../views/challenge/AnnotatorEditor.vue'),
        },
        {
          path: '/review/:unitId',
          name: 'review-video',
          meta: {
            title: '视频审核',
            requireAuth: true,
            roles: ['reviewer'],
            closable: true,
          },
          component: () => import('../views/challenge/ReviewerEditor.vue'),
        },
        {
          path: '/platform-admin',
          name: 'platform-admin',
          meta: {
            title: '平台租户管理',
            requireAuth: true,
            roles: ['platform-admin'],
            closable: true,
          },
          component: () => import('../views/platform/PlatformAdminWorkspace.vue'),
        },
        {
          path: '/tenant-admin',
          name: 'tenant-admin',
          meta: {
            title: '租户管理工作台',
            requireAuth: true,
            roles: ['admin', 'tenant-admin'],
            closable: true,
          },
          component: () => import('../views/tenant/TenantAdminWorkspace.vue'),
        },
        {
          path: '/challenge-admin',
          redirect: '/tenant-admin',
        },
        {
          path: '/user-info',
          name: 'user-info',
          meta: {
            title: '我的信息',
            // role: 'user-info',
            requireAuth: true,
            closable: true,
          },
          component: () => import(/* webpackChunkName: "user-info" */ '../views/system/user-info.vue'),
        },
        {
          // Stage 9.6: workflow 驱动的批次管理
          path: '/batches',
          name: 'batches-list',
          meta: {
            title: '批次管理',
            requireAuth: true,
            roles: ['admin', 'tenant-admin'],
            closable: true,
          },
          component: () => import(/* webpackChunkName: "batches" */ '../views/batches/BatchList.vue'),
        },
        {
          path: '/batches/create',
          name: 'batches-create',
          meta: {
            title: '新建批次',
            requireAuth: true,
            roles: ['admin', 'tenant-admin'],
            closable: true,
          },
          component: () => import(/* webpackChunkName: "batches" */ '../views/batches/BatchCreate.vue'),
        },
        {
          path: '/batches/:id',
          name: 'batches-detail',
          meta: {
            title: '批次详情',
            requireAuth: true,
            roles: ['admin', 'tenant-admin'],
            closable: true,
          },
          component: () => import(/* webpackChunkName: "batches" */ '../views/batches/BatchDetail.vue'),
        },
      ],
    },
  ]
})


// const modulePath = '/home.html';
router.beforeEach((to) => {
  if (!to.meta.requireAuth) return true
  if (!userAuth.value.isLogin) {
    window.location.assign(`${import.meta.env.BASE_URL}/auth.html`)
    return false
  }

  const required = to.meta.permiss
  if (required) {
    const { canAny } = usePermission()
    const keys = Array.isArray(required) ? required : [required]
    if (!canAny(keys.map(String))) return '/403'
  }

  const requiredRoles = (
    Array.isArray(to.meta.roles)
      ? to.meta.roles
      : to.meta.role
        ? [to.meta.role]
        : []
  ) as string[]
  if (requiredRoles.length > 0) {
    const ownedRoles = userAuth.value.roles ?? []
    if (!ownedRoles.includes('*') && !requiredRoles.some((role) => ownedRoles.includes(role))) return '/403'
  }
  return true
})


export default router
