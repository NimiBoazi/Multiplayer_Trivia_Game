import React from 'react';
import { socket } from '../socket';

function Helps({ helps, disabled }) { // helps = { fifty_fifty: true, call_friend: true, double_score: true }
    
    const onUseHelp = (type) => {
        if (!disabled && helps[type]) {
            socket.emit('use_help', { type });
        }
    };

    return (
        <div className="helps-panel">
            <h4>Helps:</h4>
            <button onClick={() => onUseHelp('fifty_fifty')} disabled={disabled || !helps.fifty_fifty}>
                50/50 {helps.fifty_fifty ? '✅' : '❌'}
            </button>
            <button onClick={() => onUseHelp('call_friend')} disabled={disabled || !helps.call_friend}>
                Call Friend {helps.call_friend ? '✅' : '❌'}
            </button>
            <button onClick={() => onUseHelp('double_score')} disabled={disabled || !helps.double_score}>
                Double Score {helps.double_score ? '✅' : '❌'}
            </button>
        </div>
    );
}

export default Helps;