<template>
  <div class="auth-page">
    <img
      :src="blueDafeiyu"
      class="auth-page__mascot auth-page__mascot--left"
      alt=""
      aria-hidden="true"
    />
    <img
      :src="blueDafeiyu"
      class="auth-page__mascot auth-page__mascot--right"
      alt=""
      aria-hidden="true"
    />

    <main class="auth-shell">
      <header class="auth-brand">
        <img :src="blueDafeiyu" class="auth-brand__avatar" alt="蓝色大肥鱼" />
        <div>
          <strong>大肥鱼标注台</strong>
          <span>FEIYU VIDEO ANNOTATION</span>
        </div>
      </header>

      <section class="auth-card" aria-labelledby="login-title">
        <header class="auth-card__header">
          <p class="auth-card__eyebrow">SIGN IN TO YOUR WORKSPACE</p>
          <h1 id="login-title" class="auth-card__title">登录</h1>
          <p class="auth-card__subtitle">
            选择演示身份，或使用邮箱和密码进入对应工作台
          </p>
        </header>

        <DemoLoginPanel
          v-if="demoEnabled"
          :loading-identity="demoLoading"
          @select="quickLogin"
        />

        <div v-if="demoEnabled" class="auth-card__divider">
          <span>或使用邮箱密码</span>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          size="large"
          class="auth-form"
          @submit.prevent="submitForm(formRef)"
        >
          <div class="auth-form__credentials">
            <el-form-item prop="email" :error="errors.email">
              <el-input
                v-model="form.email"
                :placeholder="t('auth.placeholder.email')"
                autocomplete="username"
                size="large"
                clearable
              >
                <template #prefix>
                  <Icon icon="lucide:mail" :width="18" />
                </template>
              </el-input>
            </el-form-item>

            <el-form-item prop="password" :error="errors.password">
              <el-input
                v-model="form.password"
                type="password"
                :placeholder="t('auth.placeholder.password')"
                autocomplete="current-password"
                size="large"
                show-password
              >
                <template #prefix>
                  <Icon icon="lucide:lock" :width="18" />
                </template>
              </el-input>
            </el-form-item>
          </div>

          <el-form-item prop="captchaText" :error="errors.captcha">
            <div class="captcha-inline">
              <el-input
                v-model="form.captchaText"
                :placeholder="t('auth.placeholder.captcha')"
                size="large"
                maxlength="6"
                clearable
                class="captcha-inline__input"
                @blur="checkCaptcha"
              >
                <template #prefix>
                  <Icon icon="lucide:shield-check" :width="18" />
                </template>
              </el-input>
              <button
                type="button"
                class="captcha-inline__image"
                title="点击刷新验证码"
                @click="reloadCaptcha"
              >
                <img
                  v-if="captchaSrc"
                  :src="captchaSrc"
                  :alt="t('auth.captcha.alt')"
                  class="captcha-inline__image-el"
                />
                <Icon v-else icon="lucide:refresh-cw" :width="20" />
              </button>
            </div>
          </el-form-item>

          <div class="auth-form__options">
            <el-checkbox v-model="form.rememberMe">
              {{ t('auth.action.rememberMe') }}
            </el-checkbox>
          </div>

          <el-button
            native-type="submit"
            type="primary"
            size="large"
            class="auth-submit-btn"
            :loading="submitLoading"
            :disabled="!captchaOk"
          >
            登录工作台
            <Icon icon="lucide:arrow-right" :width="18" />
          </el-button>
        </el-form>

        <p class="auth-card__notice">
          <Icon icon="lucide:info" :width="15" />
          Avery 演示邮箱不接收真实邮件，仅用于本地身份展示和登录。
        </p>
      </section>

      <footer class="auth-footer">
        <span>租户隔离 · 匿名审核 · 工作量统计</span>
        <a
          href="https://xn--pssy23gqgbz2d718b.com/"
          target="_blank"
          rel="noreferrer"
        >
          角色形象：蓝色大肥鱼.com
        </a>
      </footer>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, shallowRef } from 'vue'
import { Icon } from '@iconify/vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { capchaApi, demoAuthApi, systemApi, userApi } from '@/api'
import { cleanLoginfo, userAuth } from '@/states/UserState'
import { i18n } from '@/locales'
import { roleLandingPath } from '@/home/role-landing'
import blueDafeiyu from '@/assets/blue-dafeiyu.png'
import DemoLoginPanel from '../../components/DemoLoginPanel.vue'
import type { DemoIdentity } from '../../demo-identities'

const globalI18n: any = i18n
const t = (key: string) => String(globalI18n.global.t(key))

const formRef = shallowRef<FormInstance>()
const submitLoading = shallowRef(false)
const captchaOk = shallowRef(false)
const captchaId = shallowRef('')
const captchaSrc = shallowRef('')
const demoEnabled = shallowRef(import.meta.env.DEV)
const demoLoading = shallowRef<DemoIdentity | null>(null)

const errors = reactive({
  email: '',
  password: '',
  captcha: '',
})

const form = reactive({
  email: 'Avery.Annotator@example.com',
  password: 'feiyu',
  captchaText: '',
  rememberMe: true,
})

const validateEmail = (email: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)

const rules: FormRules = {
  email: [
    { required: true, message: t('auth.validation.emailRequired'), trigger: 'blur' },
    {
      validator: (_rule, value, callback) => (
        validateEmail(value) ? callback() : callback(new Error(t('auth.validation.emailInvalid')))
      ),
      trigger: 'blur',
    },
  ],
  password: [
    { required: true, message: t('auth.validation.passwordRequired'), trigger: 'blur' },
    { min: 6, max: 50, message: t('auth.validation.passwordLength'), trigger: 'blur' },
  ],
  captchaText: [
    { required: true, message: t('auth.validation.captchaRequired'), trigger: 'blur' },
    { min: 6, max: 6, message: t('auth.validation.captchaLength'), trigger: 'blur' },
  ],
}

const clearErrors = () => {
  errors.email = ''
  errors.password = ''
  errors.captcha = ''
}

const reloadCaptcha = () => {
  fetch(capchaApi.imgUri, { method: 'POST' })
    .then((response) => {
      if (!response.ok) throw new Error(`${response.status}`)
      captchaId.value = response.headers.get('captcha-id') || ''
      return response.blob()
    })
    .then((blob) => {
      captchaSrc.value = URL.createObjectURL(blob)
      captchaOk.value = false
      form.captchaText = ''
    })
    .catch(() => {
      ElMessage.error(t('auth.error.captchaLoadFailed'))
    })
}

const checkCaptcha = () => {
  if (form.captchaText.length !== 6) return
  clearErrors()
  fetch(capchaApi.checkUri, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: captchaId.value, text: form.captchaText }),
  })
    .then((response) => response.json().then((body) => ({ ok: response.ok, body })))
    .then(({ ok, body }) => {
      if (ok && body.status === 200) {
        captchaOk.value = true
        return
      }
      captchaOk.value = false
      errors.captcha = t('auth.error.captchaWrong')
      form.captchaText = ''
      reloadCaptcha()
    })
    .catch(() => {
      errors.captcha = t('auth.error.captchaCheckFailed')
    })
}

const finishLogin = async (data: any, remember: boolean) => {
  userAuth.value.access_token = data.access_token
  userAuth.value.refresh_token = remember ? (data.refresh_token || '') : ''
  userAuth.value.expires_at = Date.now() + (data.expires_in ?? 1800) * 1000
  userAuth.value.token_type = 'jwt'
  userAuth.value.isLogin = true

  const userInfo = await systemApi.user_info({})
  userAuth.value.user = userInfo.data.user
  userAuth.value.roles = userInfo.data.roles
  userAuth.value.permissions = userInfo.data.permissions
  const config = await systemApi.config({})
  userAuth.value.config = config.data
  ElMessage.success(t('auth.message.loginSuccess'))

  const target = roleLandingPath(userAuth.value.roles ?? [])
  setTimeout(() => {
    window.location.href = `${import.meta.env.BASE_URL}/home.html#${target}`
  }, 500)
}

const quickLogin = async (identity: DemoIdentity) => {
  if (demoLoading.value) return
  demoLoading.value = identity
  try {
    const response = await demoAuthApi.login(identity)
    await finishLogin(response.data, true)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '演示登录失败')
  } finally {
    demoLoading.value = null
  }
}

const submitForm = async (formElement: FormInstance | undefined) => {
  if (!formElement) return
  clearErrors()
  const valid = await formElement.validate().catch(() => false)
  if (!valid || !captchaOk.value) return

  submitLoading.value = true
  try {
    const response = await userApi.login(
      {
        email: form.email,
        password: form.password,
        captchaId: captchaId.value,
        captchaText: form.captchaText,
        accountType: '2',
        mobile_phone_no: '',
        mobileMsgCode: '',
        useMobileMsgCode: false,
      },
      { 'X-Captcha-Id': captchaId.value },
    )
    await finishLogin(response.data, form.rememberMe)
  } catch (error: any) {
    if (error.kind === 'auth') {
      errors.password = t('auth.error.loginFailed')
    } else if (error.kind === 'validation') {
      errors.captcha = t('auth.error.captchaWrong')
      reloadCaptcha()
    }
  } finally {
    submitLoading.value = false
  }
}

onMounted(() => {
  if (userAuth.value.isLogin && (userAuth.value.access_token || userAuth.value.refresh_token)) {
    const target = roleLandingPath(userAuth.value.roles ?? [])
    window.location.href = `${import.meta.env.BASE_URL}/home.html#${target}`
    return
  }
  cleanLoginfo()
  reloadCaptcha()
  demoAuthApi
    .status()
    .then((response) => {
      demoEnabled.value = Boolean(response.data?.enabled) || import.meta.env.DEV
    })
    .catch(() => {
      demoEnabled.value = import.meta.env.DEV
    })
})
</script>

<style scoped>
.auth-page {
  position: relative;
  display: grid;
  min-height: 100vh;
  overflow: hidden auto;
  place-items: center;
  padding: 32px 20px;
  color: var(--lab-ink);
  background:
    radial-gradient(circle at 14% 16%, rgba(91, 192, 255, 0.17), transparent 26%),
    radial-gradient(circle at 86% 78%, rgba(22, 119, 255, 0.13), transparent 28%),
    linear-gradient(150deg, #fbfdff 0%, #eff8ff 54%, #e4f2ff 100%);
}

.auth-page::before {
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(22, 119, 255, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(22, 119, 255, 0.045) 1px, transparent 1px);
  background-size: 46px 46px;
  content: '';
  mask-image: radial-gradient(circle at center, #000 10%, transparent 82%);
  pointer-events: none;
}

.auth-page__mascot {
  position: fixed;
  z-index: 0;
  width: 340px;
  max-width: 34vw;
  pointer-events: none;
  user-select: none;
}

.auth-page__mascot--left {
  bottom: -74px;
  left: -70px;
  opacity: 0.16;
  transform: rotate(-7deg);
  filter: saturate(0.85);
}

.auth-page__mascot--right {
  top: -70px;
  right: -45px;
  width: 250px;
  opacity: 0.08;
  transform: rotate(10deg);
}

.auth-shell {
  position: relative;
  z-index: 1;
  display: flex;
  width: min(100%, 720px);
  flex-direction: column;
  align-items: center;
}

.auth-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.auth-brand__avatar {
  width: 46px;
  height: 46px;
  object-fit: contain;
  filter: drop-shadow(0 8px 12px rgba(25, 105, 181, 0.16));
}

.auth-brand div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.auth-brand strong {
  color: var(--lab-ink);
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.035em;
}

.auth-brand span {
  color: var(--lab-ash);
  font-family: var(--y-font-family-mono);
  font-size: 9px;
  letter-spacing: 0.14em;
}

.auth-card {
  width: 100%;
  padding: 32px 38px 26px;
  border: 1px solid rgba(22, 119, 255, 0.14);
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 30px 80px rgba(33, 98, 160, 0.14);
  backdrop-filter: blur(18px);
}

.auth-card__header {
  margin-bottom: 22px;
  text-align: center;
}

.auth-card__eyebrow {
  margin: 0 0 7px;
  color: #2b79bf;
  font-family: var(--y-font-family-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.13em;
}

.auth-card__title {
  margin: 0;
  color: var(--lab-ink);
  font-size: 38px;
  font-weight: 700;
  letter-spacing: -0.05em;
}

.auth-card__subtitle {
  margin: 7px 0 0;
  color: var(--lab-ash);
  font-size: 13px;
}

.auth-card__divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 22px 0 16px;
  color: var(--lab-ash);
  font-size: 11px;
}

.auth-card__divider::before,
.auth-card__divider::after {
  height: 1px;
  flex: 1;
  background: var(--lab-hairline);
  content: '';
}

.auth-form__credentials {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.auth-form :deep(.el-form-item) {
  margin-bottom: 13px;
}

.auth-form :deep(.el-input__wrapper) {
  min-height: 46px;
  border: 1px solid #dceaf6;
  border-radius: 11px;
  background: #f8fcff;
  box-shadow: none !important;
}

.auth-form :deep(.el-input__wrapper:hover) {
  border-color: #a9cef2;
}

.auth-form :deep(.el-input__wrapper.is-focus) {
  border-color: #1677ff;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(22, 119, 255, 0.08) !important;
}

.auth-form :deep(.el-input__inner) {
  color: var(--lab-ink);
  font-size: 14px;
}

.auth-form__options {
  margin: 2px 0 14px;
}

.auth-form :deep(.el-checkbox__label) {
  color: var(--lab-slate);
  font-size: 12px;
}

.auth-submit-btn {
  width: 100%;
  min-height: 46px;
  border: 0;
  border-radius: 11px;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  background: linear-gradient(135deg, #1687f8, #1267de);
  box-shadow: 0 10px 22px rgba(22, 119, 255, 0.2);
}

.auth-submit-btn :deep(span) {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.auth-submit-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #0d78e9, #0d59c8);
  transform: translateY(-1px);
}

.auth-submit-btn:disabled {
  color: #93a9bc;
  background: #edf4fa;
  box-shadow: none;
}

.captcha-inline {
  display: flex;
  width: 100%;
  gap: 8px;
}

.captcha-inline__input {
  flex: 1;
}

.captcha-inline__image {
  display: grid;
  width: 116px;
  height: 46px;
  flex: 0 0 116px;
  place-items: center;
  overflow: hidden;
  padding: 0;
  border: 1px solid #dceaf6;
  border-radius: 11px;
  color: var(--lab-ash);
  background: #f8fcff;
  cursor: pointer;
}

.captcha-inline__image:hover {
  border-color: #a9cef2;
}

.captcha-inline__image-el {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.auth-card__notice {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 7px;
  margin: 15px 0 0;
  color: var(--lab-ash);
  font-size: 11px;
  line-height: 1.55;
}

.auth-card__notice :deep(svg) {
  flex: 0 0 auto;
  margin-top: 1px;
}

.auth-footer {
  display: flex;
  width: 100%;
  justify-content: space-between;
  gap: 16px;
  margin-top: 16px;
  padding-inline: 4px;
  color: var(--lab-ash);
  font-size: 10px;
}

.auth-footer a {
  color: #2b79bf;
  text-decoration: none;
}

.auth-footer a:hover {
  text-decoration: underline;
}

@media (max-width: 680px) {
  .auth-page {
    display: block;
    padding: 16px;
  }

  .auth-shell {
    margin: 0 auto;
  }

  .auth-page__mascot--left {
    bottom: -32px;
    left: -48px;
    width: 220px;
    opacity: 0.12;
  }

  .auth-page__mascot--right {
    display: none;
  }

  .auth-card {
    padding: 24px 18px;
    border-radius: 20px;
  }

  .auth-card__title {
    font-size: 32px;
  }

  .auth-form__credentials {
    grid-template-columns: 1fr;
    gap: 0;
  }

  .auth-footer {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
}
</style>
