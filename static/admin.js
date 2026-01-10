// 載入目前設定
async function loadConfig() {
  const res = await fetch("/config");
  const config = await res.json();

  document.getElementById("acceptResponses").checked = config.accept_responses;
  document.getElementById("deadline").value = config.deadline;
}

// 更新設定
document.getElementById("configForm").addEventListener("submit", async function(e) {
  e.preventDefault();

  const payload = {
    accept_responses: document.getElementById("acceptResponses").checked,
    deadline: document.getElementById("deadline").value
  };

  const res = await fetch("/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  const result = await res.json();
  if (result.success) {
    alert("設定已更新！");
  } else {
    alert("更新失敗：" + result.error);
  }
});

// 初始化載入
loadConfig();