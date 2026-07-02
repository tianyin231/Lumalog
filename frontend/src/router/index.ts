import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('../pages/DashboardPage.vue'),
    },
    {
      path: '/weight',
      name: 'weight',
      component: () => import('../pages/WeightPage.vue'),
    },
    {
      path: '/food',
      name: 'food',
      component: () => import('../pages/FoodPage.vue'),
    },
    {
      path: '/exercise',
      name: 'exercise',
      component: () => import('../pages/ExercisePage.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../pages/SettingsPage.vue'),
    },
  ],
})

export default router
