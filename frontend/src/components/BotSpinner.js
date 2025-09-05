import React from 'react';

const BotSpinner = () => (
    <div style={{
        position: 'fixed', bottom: '20px', right: '20px',
        background: 'rgba(0,0,0,0.7)', color: 'white', padding: '10px', borderRadius: '5px'
    }}>
        Bots are thinking... 🤖
    </div>
);
export default BotSpinner;