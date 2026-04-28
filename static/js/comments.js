/* ===== LOGIQUE DES COMMENTAIRES VYBE ===== */

let scrollLoop = null;
let isUserReading = false;

// GÉNÉRATION (Look YouTube)
function renderComments(videoId) {
    const content = document.getElementById("commentContent");
    if(!content) return;

    content.innerHTML = Array.from({length: 6}, (_, i) => {
        const cid = (parseInt(videoId) * 100) + i; 

        return `
        <div class="comment-item" id="comment-${cid}">
            <div style="display:flex; gap:12px;">
                <div style="width:35px; height:35px; background:linear-gradient(45deg, #ff4b2b, #ff416c); border-radius:50%; flex-shrink:0;"></div>
                <div style="flex:1;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="font-size:13px; color:#eee;">@vibeur_${cid}</strong>
                    </div>

                    <p id="comment-text-${cid}" style="font-size:13px; color:#ccc; margin:5px 0;">
                        C'est le commentaire n°${i+1} pour la vidéo ${videoId} ! 🔥
                    </p>

                    <div class="comment-footer" style="display: flex; align-items: center; justify-content: space-between; margin-top: 8px;">
                        <div style="display: flex; gap: 12px; align-items: center;">
                            <span class="action-btn" onclick="handleReaction(${cid}, 'like')" style="cursor:pointer; font-size: 12px;">
                                👍 <small id="like-count-${cid}">12</small>
                            </span>
                            <span class="action-btn" onclick="setupReply(${cid})" style="cursor:pointer; font-size: 12px; color: #888;">
                                Répondre
                            </span>
                        </div>
                        
                        <div class="user-controls" style="display: flex; gap: 10px; align-items: center; opacity: 0.8;">
                            <span class="action-btn" onclick="editComment(${cid})" style="cursor:pointer; font-size: 14px;">✏️</span>
                            <span class="action-btn" onclick="deleteComment(${cid})" style="color:#ff4b2b; cursor:pointer; font-size: 14px;">🗑️</span>
                        </div>
                    </div>

                    <div id="reply-sector-${cid}" class="reply-container"></div>
                </div>
            </div>
        </div>`;
    }).join('');
}

function openComments(id){
    const panel = document.getElementById("commentPanel");
    const backdrop = document.getElementById("commentBackdrop");
    const content = document.getElementById("commentContent");

    if(!panel || !backdrop || !content) return;

    panel.classList.add("active");
    backdrop.classList.add("active");
    document.body.style.overflow = "hidden";
    
    renderComments(id || activeVideoId);

    content.onmouseenter = () => isUserReading = true;
    content.onmouseleave = () => isUserReading = false;
    content.ontouchstart = () => isUserReading = true;
    content.ontouchend = () => isUserReading = false;

    cancelAnimationFrame(scrollLoop);
    function autoScroll(){
        if (!isUserReading) { content.scrollTop += 0.5; }
        scrollLoop = requestAnimationFrame(autoScroll);
    }
    autoScroll();
}

function closeComments(){
    const panel = document.getElementById("commentPanel");
    const backdrop = document.getElementById("commentBackdrop");
    if(panel) panel.classList.remove("active");
    if(backdrop) backdrop.classList.remove("active");

    document.body.style.overflow = "auto";
    cancelAnimationFrame(scrollLoop);
    scrollLoop = null;
}

function handleReaction(commentId, type) {
    const likeCountEl = document.getElementById(`like-count-${commentId}`);
    if(!likeCountEl) return;
    const likeBtn = likeCountEl.parentElement;

    if(type === 'like'){
        likeBtn.style.color = "#ff4b2b";
        likeCountEl.innerText = parseInt(likeCountEl.innerText) + 1;
    }
}

function editComment(commentId){
    const el = document.getElementById(`comment-text-${commentId}`);
    if(!el) return;
    const oldText = el.innerText;
    isUserReading = true;

    el.innerHTML = `
        <input type="text" value="${oldText}" id="edit-${commentId}" 
        style="width:100%; background:rgba(255,255,255,0.1); border:1px solid #444; color:white; padding:4px; border-radius:5px; outline:none;">
    `;

    const input = document.getElementById(`edit-${commentId}`);
    input.focus();

    const saveContent = () => {
        el.innerText = input.value.trim() || oldText;
        isUserReading = false;
    };

    input.onblur = saveContent;
    input.onkeydown = (e) => {
        if(e.key === "Enter") saveContent();
        if(e.key === "Escape") { el.innerText = oldText; isUserReading = false; }
    };
}

function deleteComment(commentId) {
    if(confirm("Supprimer ce commentaire ?")) {
        const el = document.getElementById(`comment-${commentId}`);
        if(el) el.remove();
    }
}

function setupReply(commentId) {
    const sector = document.getElementById(`reply-sector-${commentId}`);
    if(!sector || document.getElementById(`input-${commentId}`)) return;

    sector.innerHTML += `
        <div style="margin-top:10px; display:flex; gap:5px;">
            <input type="text" id="input-${commentId}" placeholder="Répondre..." 
                style="flex:1; background:rgba(255,255,255,0.1); border:none; color:white; padding:5px 10px; border-radius:15px; font-size:12px; outline:none;">
            <button onclick="this.parentElement.remove()" style="background:none; border:none; color:#888; cursor:pointer;">✕</button>
        </div>
    `;
    document.getElementById(`input-${commentId}`).focus();
}