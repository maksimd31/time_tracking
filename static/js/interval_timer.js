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
        const hours = Math.floor(this.elapsedSeconds / 3600);
        const minutes = Math.floor((this.elapsedSeconds % 3600) / 60);
        const seconds = this.elapsedSeconds % 60;
        const el = document.getElementById("time");
        if (el) {
            el.textContent = `${hours} ч ${minutes.toString().padStart(2, '0')} мин ${seconds.toString().padStart(2, '0')} секунд`;
        }
    }
};

document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("time")) {
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