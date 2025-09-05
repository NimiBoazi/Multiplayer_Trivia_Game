import React, { useState, useEffect } from 'react';
import { socket } from '../socket';

function Options({ options, correctAnswer, disabled, isSpectating }) {
    const [selectedOption, setSelectedOption] = useState(null);
    const [submitted, setSubmitted] = useState(false);

    useEffect(() => {
        setSelectedOption(null);
        setSubmitted(false);
    }, [options]); // Reset on new question (options change)

    const handleOptionClick = (option) => {
        if (disabled || submitted || isSpectating) return; // Check isSpectating
        setSelectedOption(option);
        socket.emit('submit_answer', { answer: option });
        setSubmitted(true);
    };

    return (
        <div className="options-container">
            {options.map((option, index) => (
                <button
                    key={index}
                    className={`
                        option-button
                        ${selectedOption === option ? 'selected' : ''}
                        ${(disabled && !isSpectating && option === correctAnswer) ? 'correct' : ''} 
                        ${(disabled && !isSpectating && selectedOption === option && option !== correctAnswer) ? 'incorrect' : ''}
                        ${isSpectating ? 'spectator-option' : ''}
                    `}
                    onClick={() => handleOptionClick(option)}
                    disabled={disabled || submitted || isSpectating}
                >
                    {option}
                </button>
            ))}
            {submitted && !disabled && !isSpectating && <p>Waiting for others...</p>}
        </div>
    );
}

export default Options;