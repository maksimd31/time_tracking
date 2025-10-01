// let elapsedSeconds = 0;
//
// function updateElapsedTime() {
//     const hours = Math.floor(elapsedSeconds / 3600);
//     const minutes = Math.floor((elapsedSeconds % 3600) / 60);
//     const seconds = elapsedSeconds % 60;
//
//     let formatted = `${hours} ч ${minutes.toString().padStart(2, '0')} мин ${seconds.toString().padStart(2, '0')} секунд`;
//
//     document.getElementById('time').textContent = formatted;
//     elapsedSeconds++;
// }
//
// setInterval(updateElapsedTime, 1000);
// updateElapsedTime();

function pad(num) {
    return num.toString().padStart(2, '0');
}

function hourWord(value) {
    if (value % 100 >= 11 && value % 100 <= 14) {
        return 'часов';
    }
    const tail = value % 10;
    if (tail === 1) return 'час';
    if (tail >= 2 && tail <= 4) return 'часа';
    return 'часов';
}

function formatDuration(secondsTotal) {
    const safeSeconds = Math.max(0, Math.floor(secondsTotal));
    const hours = Math.floor(safeSeconds / 3600);
    const minutes = Math.floor((safeSeconds % 3600) / 60);
    const seconds = safeSeconds % 60;

    if (hours === 0) {
        return `${pad(minutes)}:${pad(seconds)}`;
    }

    return `${hours} ${hourWord(hours)} ${pad(minutes)}:${pad(seconds)}`;
}

function fromLegacyFormat(text) {
    if (!text) return null;
    const trimmed = text.trim();
    const legacy = trimmed.match(/^(\d+)\s*ч\s*(\d{2})\s*мин\s*(\d{2})\s*(?:секунд|сек)?$/i);
    if (!legacy) {
        return null;
    }
    const hours = parseInt(legacy[1], 10);
    const minutes = parseInt(legacy[2], 10);
    const seconds = parseInt(legacy[3], 10);
    if (Number.isNaN(hours) || Number.isNaN(minutes) || Number.isNaN(seconds)) {
        return null;
    }
    if (hours === 0) {
        return `${pad(minutes)}:${pad(seconds)}`;
    }
    return `${hours} ${hourWord(hours)} ${pad(minutes)}:${pad(seconds)}`;
}

let intervalTimer = {
    elapsedSeconds: 0,
    intervalId: null,
    start() {
        if (this.intervalId !== null) return; // уже работает
        this.elapsedSeconds = 0;
        this.update();
        this.intervalId = setInterval(() => {
            this.elapsedSeconds++;
            this.update();
        }, 1000);
    },
    stop() {
        if (this.intervalId !== null) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        this.elapsedSeconds = 0;
    },
    update() {
        const el = document.getElementById("time");
        if (el) {
            el.textContent = formatDuration(this.elapsedSeconds);
        }
    }
};

document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("time")) {
        const legacy = fromLegacyFormat(document.getElementById("time").textContent);
        if (legacy) {
            document.getElementById("time").textContent = legacy;
        }
        intervalTimer.start();
    }
});

document.body.addEventListener("htmx:beforeSwap", (event) => {
    if (event.target === document.body) {
        intervalTimer.stop();
    }
});

document.body.addEventListener("htmx:afterSwap", (event) => {
    if (event.target === document.body && document.getElementById("time")) {
        intervalTimer.start();
    }
});
