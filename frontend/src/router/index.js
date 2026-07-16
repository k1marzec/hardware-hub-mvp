import { createRouter, createWebHistory } from 'vue-router'

import { useAuth } from '../stores/auth'

import DashboardLayout from '../layouts/DashboardLayout.vue'
import AdminPanelView from '../views/AdminPanelView.vue'
import HardwareListView from '../views/HardwareListView.vue'
import LoginView from '../views/LoginView.vue'
import MyRentalsView from '../views/MyRentalsView.vue'

const routes = [
  { path: '/login', name: 'login', component: LoginView },
  {
    path: '/',
    component: DashboardLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/hardware' },
      { path: 'hardware', name: 'hardware', component: HardwareListView },
      { path: 'rentals', name: 'rentals', component: MyRentalsView },
      {
        path: 'admin',
        name: 'admin',
        component: AdminPanelView,
        meta: { requiresAdmin: true },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/hardware' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const { isAuthenticated, isAdmin } = useAuth()

  if (to.meta.requiresAuth && !isAuthenticated.value) {
    return { name: 'login' }
  }
  if (to.meta.requiresAdmin && !isAdmin.value) {
    return { name: 'hardware' }
  }
  if (to.name === 'login' && isAuthenticated.value) {
    return { name: 'hardware' }
  }
  return true
})

export default router
