// ======================
// Spotify 搜尋建議
// ======================
document.getElementById("songName").addEventListener("input", async function() {
  const query = this.value;
  if (query.length < 2) {
    document.getElementById("suggestions").innerHTML = "";
    return;
  }

  try {
    const res = await fetch(`/search?q=${encodeURIComponent(query)}`);
    const data = await res.json();

    const suggestions = document.getElementById("suggestions");
    suggestions.innerHTML = "";

    if (data.error) {
      const div = document.createElement("div");
      div.className = "list-group-item text-danger";
      div.textContent = "搜尋失敗：" + data.error;
      suggestions.appendChild(div);
      return;
    }

    data.forEach(item => {
      const div = document.createElement("div");
      div.className = "list-group-item list-group-item-action";
      div.textContent = `${item.name} - ${item.artist}`;
      div.onclick = () => {
        document.getElementById("songName").value = item.name;
        document.getElementById("songLink").value = item.url;
        suggestions.innerHTML = "";
      };
      suggestions.appendChild(div);
    });
  } catch (err) {
    console.error("Spotify 搜尋錯誤:", err);
  }
});

// ======================
// 表單送出
// ======================
document.getElementById("songForm").addEventListener("submit", async function(e) {
  e.preventDefault();

  const payload = {
    name: document.getElementById("name").value,
    gender: document.getElementById("gender").value,
    songName: document.getElementById("songName").value,
    songLink: document.getElementById("songLink").value
  };

  try {
    const res = await fetch("/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const result = await res.json();
    if (result.success) {
      alert("送出成功！");
      this.reset();
    } else {
      alert("送出失敗：" + result.error);
    }
  } catch (err) {
    console.error("送出錯誤:", err);
    alert("送出失敗，請稍後再試。");
  }
});