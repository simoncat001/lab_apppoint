import {
    createRouter,
    createWebHistory,
    type NavigationGuardNext,
    type RouteLocationNormalized,
    type RouteRecordRaw,
} from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Layout from '@/components/layout/Layout.vue'

const routes: RouteRecordRaw[] = [
    {
        path: '/login',
        name: 'Login',
        component: () => import('@/views/auth/Login.vue'),
        meta: { requiresAuth: false, title: '登录' },
    },
    {
        path: '/register',
        name: 'Register',
        component: () => import('@/views/auth/Register.vue'),
        meta: { requiresAuth: false, title: '注册' },
    },
    {
        path: '/',
        component: Layout,
        redirect: '/dashboard',
        meta: { requiresAuth: true },
        children: [
            {
                path: 'project-context',
                name: 'ProjectWorkspaceSelect',
                component: () => import('@/views/projects/ProjectWorkspaceSelect.vue'),
                meta: { title: '选择项目', requiresProject: false },
            },
            {
                path: 'project-access-request',
                name: 'ProjectAccessRequest',
                component: () => import('@/views/projects/ProjectAccessRequest.vue'),
                meta: { title: '项目预约权限申请', requiresProject: false },
            },
            {
                path: 'account-membership-request',
                name: 'AccountMembershipRequest',
                component: () => import('@/views/accounts/AccountMembershipRequest.vue'),
                meta: { title: '所属账户申请', requiresProject: false, externalOnly: true },
            },
            {
                path: 'account-membership-approval',
                name: 'AccountMembershipApproval',
                component: () => import('@/views/accounts/AccountMembershipApproval.vue'),
                meta: { title: '所属账户审批', requiresProject: false, requiresStaff: true },
            },
            {
                path: 'project-access-approval',
                name: 'ProjectAccessApproval',
                component: () => import('@/views/projects/ProjectAccessApproval.vue'),
                meta: { title: '项目预约权限审批' },
            },
            {
                path: 'dashboard',
                name: 'Dashboard',
                component: () => import('@/views/dashboard/Dashboard.vue'),
                meta: { title: '仪表盘' },
            },
            // 用户管理
            {
                path: 'users',
                name: 'UserList',
                component: () => import('@/views/user/UserList.vue'),
                meta: { title: '用户列表', requiresStaff: true },
            },
            {
                path: 'accounts',
                name: 'Accounts',
                component: () => import('@/views/accounts/AccountList.vue'),
                meta: { title: '账户管理', requiresStaff: true },
            },
            {
                path: 'accounts/new',
                name: 'AccountCreate',
                component: () => import('@/views/accounts/AccountForm.vue'),
                meta: { title: '创建账户', requiresStaff: true },
            },
            {
                path: 'accounts/:id/edit',
                name: 'AccountEdit',
                component: () => import('@/views/accounts/AccountForm.vue'),
                meta: { title: '账户配置', requiresStaff: true },
            },
            // 仪器管理
            {
                path: 'tools',
                name: 'Tools',
                component: () => import('@/views/tools/ToolList.vue'),
                meta: { title: '仪器列表' },
            },
            {
                path: 'tools/new',
                name: 'ToolCreate',
                component: () => import('@/views/tools/ToolEdit.vue'),
                meta: { title: '创建仪器', requiresStaff: true },
            },
            {
                path: 'tools/:id/edit',
                name: 'ToolEdit',
                component: () => import('@/views/tools/ToolEdit.vue'),
                meta: { title: '编辑仪器', requiresStaff: true },
            },
            {
                path: 'tool-control',
                name: 'ToolControl',
                component: () => import('@/views/tools/ToolControl.vue'),
                meta: { title: '仪器控制', requiresStaff: true },
            },
            {
                path: 'tools/:id',
                name: 'ToolDetail',
                component: () => import('@/views/tools/ToolDetail.vue'),
                meta: { title: '仪器详情' },
            },
            // 预约管理
            {
                path: 'reservations',
                name: 'Reservations',
                component: () => import('@/views/reservations/ReservationList.vue'),
                meta: { title: '预约列表', requiresVerified: true },
            },
            {
                path: 'reservations/new',
                name: 'ReservationCreate',
                component: () => import('@/views/reservations/ReservationCreate.vue'),
                meta: { title: '创建预约', requiresVerified: true },
            },
            {
                path: 'calendar',
                name: 'Calendar',
                component: () => import('@/views/reservations/Calendar.vue'),
                meta: { title: '预约日历', requiresVerified: true },
            },
            {
                path: 'billing',
                name: 'Billing',
                component: () => import('@/views/billing/BillList.vue'),
                meta: { title: '账单' },
            },
            {
                path: 'billing/:id',
                name: 'BillDetail',
                component: () => import('@/views/billing/BillDetail.vue'),
                meta: { title: '账单详情' },
            },
            // 使用记录
            {
                path: 'usage-events',
                name: 'UsageEvents',
                component: () => import('@/views/usage-events/UsageEventList.vue'),
                meta: { title: '使用记录' },
            },
            {
                path: 'collaboration-records',
                name: 'CollaborationRecords',
                component: () => import('@/views/collaboration/CollaborationRecordList.vue'),
                meta: { title: '科研协作记录' },
            },
            {
                path: 'collaboration-records/new',
                name: 'CollaborationRecordCreate',
                component: () => import('@/views/collaboration/CollaborationRecordEdit.vue'),
                meta: { title: '新增协作记录' },
            },
            {
                path: 'collaboration-records/:id(\\d+)/edit',
                name: 'CollaborationRecordEdit',
                component: () => import('@/views/collaboration/CollaborationRecordEdit.vue'),
                meta: { title: '编辑协作记录' },
            },
            {
                path: 'collaboration-records/:id(\\d+)',
                name: 'CollaborationRecordDetail',
                component: () => import('@/views/collaboration/CollaborationRecordDetail.vue'),
                meta: { title: '协作记录详情' },
            },
            // 任务管理
            {
                path: 'tasks',
                name: 'Tasks',
                component: () => import('@/views/tasks/TaskList.vue'),
                meta: { title: '任务列表' },
            },
            {
                path: 'tasks/:id',
                name: 'TaskDetail',
                component: () => import('@/views/tasks/TaskDetail.vue'),
                meta: { title: '任务详情' },
            },
            // 员工收费
            {
                path: 'staff-charges',
                name: 'StaffCharges',
                component: () => import('@/views/staff-charges/StaffChargeList.vue'),
                meta: { title: '员工收费', requiresStaff: true },
            },
            // 配置管理
            {
                path: 'configurations',
                name: 'Configurations',
                component: () => import('@/views/configurations/ConfigurationList.vue'),
                meta: { title: '配置管理', requiresStaff: true },
            },
            // 公告
            {
                path: 'announcements',
                name: 'Announcements',
                component: () => import('@/views/announcements/AnnouncementList.vue'),
                meta: { title: '公告' },
            },
            {
                path: 'announcements/new',
                name: 'AnnouncementCreate',
                component: () => import('@/views/announcements/AnnouncementEdit.vue'),
                meta: { title: '发布公告', requiresStaff: true },
            },
            {
                path: 'announcements/:id(\\d+)/edit',
                name: 'AnnouncementEdit',
                component: () => import('@/views/announcements/AnnouncementEdit.vue'),
                meta: { title: '编辑公告', requiresStaff: true },
            },
            {
                path: 'announcements/:id(\\d+)',
                name: 'AnnouncementDetail',
                component: () => import('@/views/announcements/AnnouncementDetail.vue'),
                meta: { title: '公告详情' },
            },
            // 培训与考试
            {
                path: 'training',
                name: 'Training',
                component: () => import('@/views/training/TrainingCenter.vue'),
                meta: { title: '培训与考试', requiresAuth: true },
            },
            {
                path: 'training/contents/:id',
                name: 'TrainingContentDetail',
                component: () => import('@/views/training/TrainingContentDetail.vue'),
                meta: { title: '学习资料详情', requiresAuth: true },
            },
            // 维保记录
            {
                path: 'maintenance',
                name: 'Maintenance',
                component: () => import('@/views/maintenance/MaintenanceList.vue'),
                meta: { title: '维保记录', requiresStaff: true },
            },
            // 报表
            {
                path: 'reports',
                name: 'Reports',
                component: () => import('@/views/reports/ReportDashboard.vue'),
                meta: { title: '数据报表', requiresStaff: true, requiresSuperuser: true },
            },
            // 用户设置
            {
                path: 'profile',
                name: 'Profile',
                component: () => import('@/views/user/Profile.vue'),
                meta: { title: '个人资料', requiresProject: false },
            },
        ],
    },
    // ---------- Staff (internal-employee) area ----------
    // Mounted at /security/*. Has its OWN layout, auth store and login
    // page, so it bypasses every nemo-side guard (requiresAuth /
    // requiresProject / project context). `meta.staffArea` is the marker
    // the global guard uses to flip into staff-auth mode.
    {
        path: '/security/login',
        name: 'StaffLogin',
        component: () => import('@/security/views/LoginView.vue'),
        meta: { requiresAuth: false, staffArea: true, public: true, title: '内部员工登录' },
    },
    {
        path: '/security',
        component: () => import('@/security/layouts/AppShell.vue'),
        redirect: '/security/dashboard',
        meta: { requiresAuth: false, staffArea: true },
        children: [
            {
                path: 'dashboard',
                name: 'StaffDashboard',
                component: () => import('@/security/views/DashboardView.vue'),
                meta: { staffArea: true, title: '控制台概览', subtitle: '快速掌握组织与审批的实时状态' },
            },
            {
                path: 'departments',
                name: 'StaffDepartments',
                component: () => import('@/security/views/DepartmentsView.vue'),
                meta: { staffArea: true, title: '部门管理', subtitle: '组织架构的顶层入口' },
            },
            {
                path: 'projects',
                name: 'StaffProjects',
                component: () => import('@/security/views/ProjectsView.vue'),
                meta: { staffArea: true, title: '项目管理', subtitle: '按部门分组的项目视图' },
            },
            {
                path: 'groups',
                name: 'StaffGroups',
                component: () => import('@/security/views/GroupsView.vue'),
                meta: { staffArea: true, title: '小组管理', subtitle: '项目内协作单元的快速管理' },
            },
            {
                path: 'applications',
                name: 'StaffApplications',
                component: () => import('@/security/views/ApplicationsView.vue'),
                meta: { staffArea: true, title: '申请审批', subtitle: '统一处理加入申请与审批流程' },
            },
            {
                path: 'applications/quick',
                name: 'StaffApplicationQuick',
                component: () => import('@/security/views/ApplicationQuickView.vue'),
                meta: { staffArea: true, title: '快捷申请', subtitle: '快速提交加入申请' },
            },
            {
                path: 'users',
                name: 'StaffUsers',
                component: () => import('@/security/views/UsersView.vue'),
                meta: { staffArea: true, title: '用户管理', subtitle: '系统账号的创建与调整' },
            },
        ],
    },
    {
        path: '/:pathMatch(.*)*',
        name: 'NotFound',
        component: () => import('@/views/error/NotFound.vue'),
        meta: { requiresAuth: false, title: '404' },
    },
]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

const EXTERNAL_ALLOWED_ROUTE_NAMES = new Set<string>([
    'ProjectWorkspaceSelect',
    'ProjectAccessRequest',
    'AccountMembershipRequest',
    'Tools',
    'ToolDetail',
    'Reservations',
    'ReservationCreate',
    'Calendar',
    'Billing',
    'BillDetail',
    'CollaborationRecords',
    'CollaborationRecordCreate',
    'CollaborationRecordEdit',
    'CollaborationRecordDetail',
    'Announcements',
    'AnnouncementDetail',
    'Training',
    'TrainingContentDetail',
    'Profile',
])

function getExternalDefaultRoute(_authStore: ReturnType<typeof useAuthStore>) {
    // 外部用户的默认界面是公告
    return { name: 'Announcements' }
}

// 路由守卫
router.beforeEach(
    async (to: RouteLocationNormalized, _from: RouteLocationNormalized, next: NavigationGuardNext) => {
        const authStore = useAuthStore()

        // 设置页面标题
        const baseTitle = 'Laboratory Management System'
        document.title = to.meta.title ? `${to.meta.title} - ${baseTitle}` : baseTitle

        // ---------- Staff area (mounted under /security/*) ----------
        // Has its own auth store / login page; skip every nemo guard below.
        if (to.meta.staffArea) {
            const { useStaffAuthStore } = await import('@/security/stores/auth')
            const staff = useStaffAuthStore()
            if (!staff.token) staff.hydrate()
            if (to.meta.public) {
                if (to.name === 'StaffLogin' && staff.isAuthed) {
                    next({ name: 'StaffDashboard' })
                    return
                }
                next()
                return
            }
            if (!staff.isAuthed) {
                next({ name: 'StaffLogin' })
                return
            }
            next()
            return
        }

        // 检查是否需要认证
        if (to.meta.requiresAuth !== false) {
            if (!authStore.isAuthenticated) {
                next({ name: 'Login', query: { redirect: to.fullPath } })
                return
            }

            // 外部用户功能收敛：仅保留项目申请、所属账户申请、预约、公告和培训
            if (authStore.isExternalUser()) {
                const routeName = typeof to.name === 'string' ? to.name : ''
                if (routeName && !EXTERNAL_ALLOWED_ROUTE_NAMES.has(routeName)) {
                    next(getExternalDefaultRoute(authStore))
                    return
                }
            }

            if ((to.meta as any).externalOnly && !authStore.isExternalUser()) {
                next({ name: 'Dashboard' })
                return
            }

            // 检查是否需要管理员权限
            if (to.meta.requiresStaff && !authStore.isStaff()) {
                next({ name: 'Dashboard' })
                return
            }

            // 检查是否需要超级管理员权限
            if ((to.meta as any).requiresSuperuser && !authStore.isSuperuser()) {
                next({ name: 'Dashboard' })
                return
            }

            // 检查是否需要已验证（仅对普通用户）
            if ((to.meta as any).requiresVerified) {
                if (!authStore.canAccessReservations()) {
                    next(authStore.isExternalUser() ? { name: 'ProjectAccessRequest' } : { name: 'Dashboard' })
                    return
                }
            }

            const requiresProject = to.meta.requiresProject !== false
            if (requiresProject) {
                const currentProjectId = localStorage.getItem('current_project_id')
                if (!currentProjectId) {
                    next({ name: 'ProjectWorkspaceSelect', query: { redirect: to.fullPath } })
                    return
                }
            }
        }

        // 已登录用户访问登录页，跳转到首页
        if (to.name === 'Login' && authStore.isAuthenticated) {
            const currentProjectId = localStorage.getItem('current_project_id')
            if (!currentProjectId) {
                next({ name: 'ProjectWorkspaceSelect' })
                return
            }
            next(authStore.isExternalUser() ? { name: 'Announcements' } : { name: 'Dashboard' })
            return
        }

        next()
    }
)

export default router
