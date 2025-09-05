import React from 'react';

function Question({ text, number, total, difficulty }) {
    return (
        <div className="question-container">
            <h3>Question {number}/{total} (Difficulty: {difficulty || 'N/A'})</h3>
            <p className="question-text">{text}</p>
        </div>
    );
}

export default Question;