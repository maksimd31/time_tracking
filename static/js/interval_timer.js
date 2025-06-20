let elapsedSeconds = 0;

function updateElapsedTime() {
    const hours = Math.floor(elapsedSeconds / 3600);
    const minutes = Math.floor((elapsedSeconds % 3600) / 60);
    const seconds = elapsedSeconds % 60;

    let formatted = `${hours} ч ${minutes.toString().padStart(2, '0')} мин ${seconds.toString().padStart(2, '0')} секунд`;

    document.getElementById('time').textContent = formatted;
    elapsedSeconds++;
}

setInterval(updateElapsedTime, 1000);
updateElapsedTime();