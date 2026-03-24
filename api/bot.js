const crypto = require('crypto');
const axios = require('axios');

const APP_ID = 'cli_a927b08856b89bca';
const APP_SECRET = '8vBm7kcfN7a8COwvMNVezbbWZfnYGuKH';

let accessToken = null;
let tokenExpireTime = 0;

async function getAccessToken() {
  if (accessToken && Date.now() < tokenExpireTime) {
    return accessToken;
  }

  try {
    const response = await axios.post('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', {
      app_id: APP_ID,
      app_secret: APP_SECRET
    });

    accessToken = response.data.tenant_access_token;
    tokenExpireTime = Date.now() + (response.data.expire - 300) * 1000;
    return accessToken;
  } catch (error) {
    console.error('获取 token 失败:', error.message);
    throw error;
  }
}

function verifySignature(timestamp, nonce, body, signature) {
  const str = timestamp + nonce + body;
  const hash = crypto.createHmac('sha256', APP_SECRET).update(str).digest('hex');
  return hash === signature;
}

async function callClaudeAPI(message) {
  try {
    const response = await axios.post('https://api.anthropic.com/v1/messages', {
      model: 'claude-opus-4-6',
      max_tokens: 1024,
      messages: [
        {
          role: 'user',
          content: message
        }
      ]
    }, {
      headers: {
        'x-api-key': process.env.CLAUDE_API_KEY,
        'anthropic-version': '2023-06-01'
      }
    });

    return response.data.content[0].text;
  } catch (error) {
    console.error('调用 Claude API 失败:', error.message);
    return '抱歉，我暂时无法回复。请稍后重试。';
  }
}

async function sendMessage(receiveId, message) {
  const token = await getAccessToken();

  try {
    await axios.post('https://open.feishu.cn/open-apis/im/v1/messages', {
      receive_id: receiveId,
      msg_type: 'text',
      content: JSON.stringify({
        text: message
      })
    }, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      params: {
        receive_id_type: 'user_id'
      }
    });
  } catch (error) {
    console.error('发送消息失败:', error.message);
  }
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const signature = req.headers['x-lark-signature'];
  const timestamp = req.headers['x-lark-request-timestamp'];
  const nonce = req.headers['x-lark-request-nonce'];
  const body = JSON.stringify(req.body);

  if (!verifySignature(timestamp, nonce, body, signature)) {
    return res.status(401).json({ error: 'Invalid signature' });
  }

  const event = req.body;

  // 处理 URL 验证
  if (event.type === 'url_verification') {
    return res.json({ challenge: event.challenge });
  }

  // 处理消息事件
  if (event.type === 'event_callback' && event.event.type === 'message') {
    const message = event.event.message;
    const userId = event.event.sender.sender_id.user_id;
    const text = message.content ? JSON.parse(message.content).text : '';

    if (text) {
      try {
        const reply = await callClaudeAPI(text);
        await sendMessage(userId, reply);
      } catch (error) {
        console.error('处理消息失败:', error);
      }
    }
  }

  res.json({ code: 0 });
};
