async function sendMessage(){
    const input = document.getElementById("userInput");
    const message = input.value;
    if (message.trim() === "") return;

    //mostra messaggio utente
    const msgBox = document.getElementById("messages");
    msgBox.innerHTML += `<p class='user'><b>Tu:</b> ${message}</p>`;
    input.value = "";

    //invia messaggio al backend Flask
    const res = await fetch("http://127.0.0.1:5000/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
    });

    const data = await res.json();

    //mostra risposta bot
    msgBox.innerHTML += `<p class='bot'><b>Bot:</b> ${data.reply}</p>`;
    msgBox.scrollTop = msgBox.scrollHeight;
}