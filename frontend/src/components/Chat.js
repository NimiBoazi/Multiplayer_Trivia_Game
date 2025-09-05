import React, { useState, useEffect, useRef } from 'react';
import { socket } from '../socket';

function Chat({ messages, mySid, username, onSendMessage, onSendEmoji }) {
    const [newMessage, setNewMessage] = useState('');
    const messagesEndRef = useRef(null);
    const EMOJIS = ['👍', '😂', '😮', '🤔', '🎉', '💡'];

    const sendMessage = () => {
        if (newMessage.trim()) {
            onSendMessage?.(newMessage);
            setNewMessage('');
        }
    };

    const sendEmoji = (emoji) => {
        onSendEmoji?.(emoji);
    };

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    return (
        <div className="chat-container">
            <h4>Chat</h4>
            <div className="chat-messages">
                {messages.map((msg, index) => (
                    <div key={index} className={`chat-message ${msg.sender_sid === mySid ? 'my-message' : (msg.type === 'system' ? 'system-message' : 'other-message')}`}>
                        {msg.type !== 'system' && <strong>{msg.sender_sid === mySid ? 'You' : msg.sender_name}: </strong>}
                        {msg.text && <span>{msg.text}</span>}
                        {msg.emoji && <span className="chat-emoji">{msg.emoji}</span>}
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>
            <div className="chat-input">
                <input
                    type="text"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder="Type a message..."
                />
                <button onClick={sendMessage}>Send</button>
            </div>
            <div className="emoji-panel">
                {EMOJIS.map(emoji => (
                    <button key={emoji} onClick={() => sendEmoji(emoji)} className="emoji-button">{emoji}</button>
                ))}
            </div>
        </div>
    );
}

export default Chat;