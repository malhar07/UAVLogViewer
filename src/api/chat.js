import axios from 'axios'

export const upload = file =>
    axios.post('http://localhost:8000/upload', file,
        { headers: { 'Content-Type': 'multipart/form-data' } })

export const chat = (msg, logId) =>
    axios.post('http://localhost:8000/chat',
        null,
        { params: { msg, logId } })
