import React, { useState, useEffect } from 'react';

function Timer({ duration, questionKey }) {
    const [timeLeft, setTimeLeft] = useState(duration);

    useEffect(() => {
        // Reset timer whenever a new question arrives or duration changes
        setTimeLeft(duration);
        if (duration <= 0) return;

        const intervalId = setInterval(() => {
            setTimeLeft(prevTime => {
                if (prevTime <= 1) {
                    clearInterval(intervalId);
                    return 0;
                }
                return prevTime - 1;
            });
        }, 1000);

        return () => clearInterval(intervalId);
    }, [duration, questionKey]);

    return (
        <div className="timer">
            Time Left: <span className={timeLeft <= 5 ? "timer-low" : ""}>{timeLeft}s</span>
        </div>
    );
}

export default Timer;