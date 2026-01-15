export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.send("Bot Running");
  }

  const msg = req.body.message;
  if (!msg) return res.end();

  const chatId = msg.chat.id;
  const text = msg.text || "";

  const token = process.env.BOT_TOKEN;
  const url = `https://api.telegram.org/bot${token}/sendMessage`;

  await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text: `🤖 Reply from @nick_bypass_bot\n\nYou said: ${text}`
    })
  });

  res.end("ok");
}
