document.getElementById("forecastForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const data = new FormData(form);
  const res = await fetch(form.action, { method: "POST", body: data });
  const result = await res.json();

  const chartDiv = document.getElementById("forecastChart");
  chartDiv.innerHTML = "<h3>Forecast Results:</h3>";
  result.forEach(r => {
    chartDiv.innerHTML += `<p>${r.ds}: ${r.yhat.toFixed(2)}</p>`;
  });
});
