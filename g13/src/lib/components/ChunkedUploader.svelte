<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { onDestroy } from 'svelte';

  export let ticketId: string;
  export let disabled = false;

  const dispatch = createEventDispatcher<{
    success: { attachment: unknown };
    error: { message: string };
    progress: { percent: number; bytesUploaded: number; bytesTotal: number };
  }>();

  let fileInput: HTMLInputElement | null = null;
  let isUploading = false;
  let uploadProgress = 0;
  let currentFileName = '';
  let bytesUploaded = 0;
  let bytesTotal = 0;
  let uploadController: AbortController | null = null;
  let resumeData: { uploadUrl: string; offset: number } | null = null;

  const CHUNK_SIZE = 10 * 1024 * 1024;

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
  };

  const createUploadSession = async (file: File): Promise<{ uploadUrl: string }> => {
    const res = await fetch('/api/uploads', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: file.name,
        size: file.size,
        ticketId
      })
    });

    if (!res.ok) {
      throw new Error('Failed to create upload session');
    }

    return res.json();
  };

  const checkUploadStatus = async (uploadUrl: string): Promise<{ offset: number }> => {
    const res = await fetch(uploadUrl, {
      method: 'HEAD',
      credentials: 'include'
    });

    if (!res.ok) {
      throw new Error('Failed to check upload status');
    }

    const offset = parseInt(res.headers.get('Upload-Offset') || '0', 10);
    return { offset };
  };

  const uploadChunk = async (
    uploadUrl: string,
    file: File,
    offset: number,
    chunkSize: number
  ): Promise<{ newOffset: number; done: boolean }> => {
    const chunk = file.slice(offset, offset + chunkSize);
    const res = await fetch(uploadUrl, {
      method: 'PATCH',
      credentials: 'include',
      headers: {
        'Upload-Offset': String(offset),
        'Content-Type': 'application/offset+octet-stream'
      },
      body: chunk,
      signal: uploadController?.signal
    });

    if (res.status === 409) {
      const serverOffset = parseInt(res.headers.get('Upload-Offset') || '0', 10);
      return { newOffset: serverOffset, done: false };
    }

    if (!res.ok) {
      throw new Error(`Upload failed with status ${res.status}`);
    }

    const newOffset = parseInt(res.headers.get('Upload-Offset') || String(offset + chunk.size), 10);
    return { newOffset, done: newOffset >= file.size };
  };

  const completeUpload = async (uploadUrl: string): Promise<unknown> => {
    const res = await fetch(uploadUrl, {
      method: 'POST',
      credentials: 'include'
    });

    if (!res.ok) {
      throw new Error('Failed to complete upload');
    }

    return res.json();
  };

  const startUpload = async (file: File) => {
    if (disabled) return;

    isUploading = true;
    uploadProgress = 0;
    currentFileName = file.name;
    bytesUploaded = 0;
    bytesTotal = file.size;
    uploadController = new AbortController();

    try {
      let uploadUrl: string;
      let offset = 0;

      if (resumeData) {
        uploadUrl = resumeData.uploadUrl;
        const status = await checkUploadStatus(uploadUrl);
        offset = status.offset;
      } else {
        const session = await createUploadSession(file);
        uploadUrl = session.uploadUrl;
        offset = 0;
      }

      while (offset < file.size) {
        if (uploadController?.signal.aborted) {
          throw new Error('Upload cancelled');
        }

        const chunkSize = Math.min(CHUNK_SIZE, file.size - offset);
        const result = await uploadChunk(uploadUrl, file, offset, chunkSize);

        offset = result.newOffset;
        bytesUploaded = offset;
        uploadProgress = Math.round((offset / file.size) * 100);

        dispatch('progress', {
          percent: uploadProgress,
          bytesUploaded: bytesUploaded,
          bytesTotal: bytesTotal
        });

        resumeData = { uploadUrl, offset };
      }

      const attachment = await completeUpload(uploadUrl);

      dispatch('success', { attachment });

      resumeData = null;
      uploadProgress = 100;

      setTimeout(() => {
        isUploading = false;
        uploadProgress = 0;
        currentFileName = '';
      }, 1000);
    } catch (e) {
      if (e instanceof Error && e.name === 'AbortError') {
        dispatch('error', { message: '上传已取消' });
      } else {
        const message = e instanceof Error ? e.message : '上传失败';
        dispatch('error', { message });
      }
      isUploading = false;
    } finally {
      uploadController = null;
    }
  };

  const handleFileSelect = (e: Event) => {
    const target = e.target as HTMLInputElement;
    const file = target.files?.[0];
    if (file) {
      resumeData = null;
      startUpload(file);
    }
    if (fileInput) {
      fileInput.value = '';
    }
  };

  const cancelUpload = () => {
    if (uploadController) {
      uploadController.abort();
    }
  };

  const resumeUpload = () => {
    if (resumeData && fileInput?.files?.[0]) {
      startUpload(fileInput.files[0]);
    }
  };

  onDestroy(() => {
    if (uploadController) {
      uploadController.abort();
    }
  });
</script>

<div class="upload-wrapper">
  {#if !isUploading}
    <label class="upload-label" class:disabled={disabled}>
      <input
        type="file"
        bind:this={fileInput}
        on:change={handleFileSelect}
        disabled={disabled}
        hidden
      />
      <span class="upload-icon">📎</span>
      <span class="upload-text">{disabled ? '上传中...' : '点击上传附件'}</span>
      <span class="upload-hint">支持大文件分片上传，支持断点续传</span>
    </label>
  {:else}
    <div class="upload-progress">
      <div class="upload-header">
        <span class="upload-filename">{currentFileName}</span>
        <button class="cancel-btn" on:click={cancelUpload} disabled={uploadProgress === 100}>
          {uploadProgress === 100 ? '✓ 完成' : '取消'}
        </button>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" style="width: {uploadProgress}%" />
      </div>
      <div class="progress-info">
        <span>{uploadProgress}%</span>
        <span>{formatSize(bytesUploaded)} / {formatSize(bytesTotal)}</span>
      </div>
      {#if resumeData && uploadProgress < 100}
        <button class="resume-btn" on:click={resumeUpload}>
          断点续传
        </button>
      {/if}
    </div>
  {/if}
</div>

<style>
  .upload-wrapper {
    width: 100%;
  }

  .upload-label {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px;
    border: 2px dashed #dcdfe6;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    color: #909399;
    width: 100%;
    box-sizing: border-box;
  }

  .upload-label:hover:not(.disabled) {
    border-color: #409eff;
    background: #ecf5ff;
    color: #409eff;
  }

  .upload-label.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .upload-icon {
    font-size: 32px;
    margin-bottom: 8px;
  }

  .upload-text {
    font-size: 14px;
    font-weight: 500;
  }

  .upload-hint {
    font-size: 12px;
    margin-top: 4px;
    opacity: 0.8;
  }

  .upload-progress {
    background: #f5f7fa;
    padding: 20px;
    border-radius: 8px;
  }

  .upload-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .upload-filename {
    font-size: 14px;
    color: #303133;
    font-weight: 500;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-right: 12px;
  }

  .cancel-btn {
    padding: 6px 12px;
    background: #fff;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
    color: #606266;
    transition: all 0.2s;
  }

  .cancel-btn:hover:not(:disabled) {
    background: #fef0f0;
    border-color: #fbc4c4;
    color: #f56c6c;
  }

  .cancel-btn:disabled {
    opacity: 0.6;
    cursor: default;
  }

  .progress-bar {
    height: 8px;
    background: #e4e7ed;
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 8px;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #409eff, #66b1ff);
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .progress-info {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: #909399;
  }

  .resume-btn {
    margin-top: 12px;
    padding: 8px 16px;
    background: #67c23a;
    color: #fff;
    border: none;
    border-radius: 4px;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.2s;
  }

  .resume-btn:hover {
    background: #85ce61;
  }
</style>
