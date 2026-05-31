<script lang="ts">
  import { goto } from '$app/navigation';

  let email = '';
  let password = '';
  let error = '';
  let loading = false;

  const handleLogin = async (e: Event) => {
    e.preventDefault();
    loading = true;
    error = '';

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (res.ok) {
        goto('/tickets');
      } else {
        const data = await res.json();
        error = data.message || '登录失败';
      }
    } catch (e) {
      error = '网络错误，请稍后重试';
    } finally {
      loading = false;
    }
  };
</script>

<div class="login-container">
  <div class="login-card">
    <h1>工单协同系统</h1>
    <p class="subtitle">实时协作，高效处理</p>

    <form on:submit={handleLogin} class="login-form">
      <div class="form-group">
        <label for="email">邮箱</label>
        <input
          type="email"
          id="email"
          bind:value={email}
          placeholder="请输入邮箱"
          required
          disabled={loading}
        />
      </div>

      <div class="form-group">
        <label for="password">密码</label>
        <input
          type="password"
          id="password"
          bind:value={password}
          placeholder="请输入密码"
          required
          disabled={loading}
        />
      </div>

      {#if error}
        <div class="error-message">{error}</div>
      {/if}

      <button type="submit" class="btn-login" disabled={loading}>
        {loading ? '登录中...' : '登录'}
      </button>
    </form>

    <div class="demo-info">
      <p>Demo 账号：</p>
      <p>admin@example.com / 123456</p>
      <p>user1@example.com / 123456</p>
      <p>user2@example.com / 123456</p>
    </div>
  </div>
</div>

<style>
  .login-container {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  }

  .login-card {
    background: #fff;
    padding: 40px;
    border-radius: 12px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    width: 100%;
    max-width: 400px;
  }

  h1 {
    margin: 0 0 8px 0;
    font-size: 24px;
    color: #303133;
    text-align: center;
  }

  .subtitle {
    margin: 0 0 32px 0;
    color: #909399;
    text-align: center;
    font-size: 14px;
  }

  .login-form {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  label {
    font-size: 14px;
    color: #606266;
    font-weight: 500;
  }

  input {
    padding: 12px 16px;
    border: 1px solid #dcdfe6;
    border-radius: 8px;
    font-size: 14px;
    transition: border-color 0.2s;
  }

  input:focus {
    outline: none;
    border-color: #409eff;
  }

  input:disabled {
    background: #f5f7fa;
  }

  .error-message {
    padding: 12px;
    background: #fef0f0;
    border: 1px solid #fbc4c4;
    border-radius: 8px;
    color: #f56c6c;
    font-size: 13px;
  }

  .btn-login {
    padding: 12px;
    background: #409eff;
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
  }

  .btn-login:hover:not(:disabled) {
    background: #66b1ff;
  }

  .btn-login:disabled {
    background: #a0cfff;
    cursor: not-allowed;
  }

  .demo-info {
    margin-top: 24px;
    padding-top: 20px;
    border-top: 1px solid #ebeef5;
    font-size: 12px;
    color: #909399;
    line-height: 1.8;
  }

  .demo-info p {
    margin: 0;
  }
</style>
