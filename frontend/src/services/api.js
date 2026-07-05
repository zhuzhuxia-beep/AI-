import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5 min for AI processing
})

// Upload photo
export async function uploadPhoto(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/upload', formData)
  return data
}

// Restore photo (repair + colorize)
export async function restorePhoto(id) {
  const { data } = await api.post(`/restore/${id}`)
  return data
}

// Get photo status
export async function getPhotoStatus(id) {
  const { data } = await api.get(`/photo/${id}`)
  return data
}

// Generate story narration (TTS)
export async function generateStory(id, story) {
  const { data } = await api.post(`/story/${id}`, { story })
  return data
}

// Generate video
export async function generateVideo(id) {
  try {
    const { data } = await api.post(`/video/${id}`)
    return data
  } catch (error) {
    // Extract detailed error message from backend response
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail)
    }
    if (error.response?.data?.traceback) {
      throw new Error(`${error.response.data.detail || '视频生成失败'}\n${error.response.data.traceback}`)
    }
    throw error
  }
}

// Get gallery (completed photos for showcase)
export async function getGallery() {
  const { data } = await api.get('/gallery')
  return data
}

// Story templates to help users write
export const storyTemplates = [
  {
    label: '奶奶的故事',
    text: '这是我奶奶18岁时的照片，那年她刚考上师范学校。她总说那是她人生中最快乐的一年，每天天不亮就起床读书，晚上在煤油灯下备课。照片里的她笑得那么灿烂，仿佛整个世界都在她脚下。',
  },
  {
    label: '父母的结婚照',
    text: '这是爸妈1985年拍的结婚照。那时候没有婚纱，妈妈穿了一件红色外套，爸爸借了同事的西装。虽然条件简朴，但他们眼里的光，比任何华丽的婚纱都要美。',
  },
  {
    label: '童年全家福',
    text: '这是1988年春节拍的全家福。那年我五岁，爷爷还健在。记得拍照那天，摄影师跑了三条街才找到一台能用的相机。爷爷抱着我，笑得合不拢嘴，那是我记忆中最温暖的画面。',
  },
  {
    label: '青春岁月',
    text: '这是1990年高中毕业时的合影。那时候我们怀揣梦想，以为未来有无限可能。三十年过去了，照片里的人散落在天南海北，但每次看到这张照片，仿佛又回到了那个蝉鸣的夏天。',
  },
]
