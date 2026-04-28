/* ===== LOGIQUE DES COMMENTAIRES VYBE (VERSION COMPLÈTE & RÉELLE) ===== */

let scrollLoop = null;
let isUserReading = false;

/* ===== 1. RÉCUPÉRATION RÉELLE DEPUIS LE SERVEUR ===== */
async function renderComments(videoId) {
    const content = document.getElementById("commentContent");
    if (!content) return;

    content.innerHTML = '<div style="text-align:center; padding:20px; color:#888;">Chargement...</div>';

    try {
        const response = await fetch(`/api/get_comments/${videoId}`);
        const data = await response.json();

        if (data.comments.length === 0) {
            content.innerHTML = '<div style="text-align:center; padding:40px; color:#666;">Soyez le premier à donner votre vibe ! ✨</div>';
            return;
        }

        content.innerHTML = data.comments.map(comment => {
            return `
            <div class="comment-item" id="comment-${comment.id}">
                <div class="comment-user-flex">
                    <div class="comment-avatar">
                        <img src="${comment.user_image || '/static/uploads/default_user.jpg'}" 
                             style="width:100%; height:100%; border-radius:50%; object-fit:cover;">
                    </div>
                    <div class="comment-main-content">
                        <div class="comment-header-line">
                            <span class="comment-username">@${comment.username.toLowerCase()}</span>
                            <small style="color:#555; font-size:10px;">${comment.date_created}</small>
                        </div>
                        <div id="comment-text-${comment.id}" class="comment-text">${comment.text}</div>
                        <div class="comment-footer">
                            <div class="comment-actions-left">
                                <span class="action-btn" onclick="handleReaction(${comment.id}, 'like')" id="like-btn-${comment.id}">
                                    👍 <small id="like-count-${comment.id}">${comment.likes_count}</small>
                                </span>
                                <span class="action-btn" onclick="setupReply(${comment.id})">Répondre</span>
                            </div>
                            <div class="user-controls">
                                <span class="action-btn" onclick="editComment(${comment.id})">✏️</span>
                                <span class="action-btn" onclick="deleteComment(${comment.id})" style="color:#ff4b2b;">🗑️</span>
                            </div>
                        </div>
                        <div id="reply-sector-${comment.id}" class="reply-container"></div>
                    </div>
                </div>
            </div>`;
        }).join('');
    } catch (error) {
        content.innerHTML = '<div style="text-align:center; padding:20px; color:#e74c3c;">Erreur.</div>';
    }
}

/* ===== 2. ENVOI RÉEL EN BASE DE DONNÉES ===== */
async function sendComment() {
    const input = document.getElementById("newCommentInput");
    if (!input || !input.value.trim()) return;

    const content = input.value.trim();
    const videoId = window.currentVideoId;

    input.disabled = true;

    try {
        const response = await fetch(`/add_comment/${videoId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: content })
        });
        const data = await response.json();
        if (data.status === 'success') {
            input.value = "";
            renderComments(videoId); // On rafraîchit la liste
        }
    } catch (e) {
        alert("Erreur d'envoi");
    } finally {
        input.disabled = false;
    }
}

/* ===== 3. TON CODE ORIGINAL POUR L'OUVERTURE / SCROLL ===== */
function openComments(id) {
    const panel = document.getElementById("commentPanel");
    const backdrop = document.getElementById("commentBackdrop");
    const content = document.getElementById("commentContent");

    if (!panel || !backdrop || !content) return;

    panel.classList.add("active");
    backdrop.classList.add("active");
    document.body.style.overflow = "hidden";

    window.currentVideoId = id;
    renderComments(id);

    // Détection interaction (Ton code original)
    content.onmouseenter = () => isUserReading = true;
    content.onmouseleave = () => isUserReading = false;
    content.ontouchstart = () => isUserReading = true;
    content.ontouchend = () => isUserReading = false;

    cancelAnimationFrame(scrollLoop);
    function autoScroll() {
        if (!isUserReading && content.scrollHeight > content.clientHeight) {
            content.scrollTop += 0.4;
        }
        scrollLoop = requestAnimationFrame(autoScroll);
    }
    autoScroll();
}

function closeComments() {
    const panel = document.getElementById("commentPanel");
    const backdrop = document.getElementById("commentBackdrop");
    if (panel) panel.classList.remove("active");
    if (backdrop) backdrop.classList.remove("active");
    document.body.style.overflow = "auto";
    cancelAnimationFrame(scrollLoop);
}

/* ===== 4. RÉACTIONS, ÉDITION ET SUPPRESSION (LOGIQUE COMPLÈTE) ===== */
function handleReaction(commentId, type) {
    const likeCountEl = document.getElementById(`like-count-${commentId}`);
    const likeBtn = document.getElementById(`like-btn-${commentId}`);
    if (likeBtn.classList.contains("active-like")) {
        likeBtn.classList.remove("active-like");
        likeCountEl.innerText = Math.max(0, parseInt(likeCountEl.innerText) - 1);
    } else {
        likeBtn.classList.add("active-like");
        likeCountEl.innerText = parseInt(likeCountEl.innerText) + 1;
    }
}

function editComment(commentId) {
    const el = document.getElementById(`comment-text-${commentId}`);
    if (!el) return;
    const oldText = el.innerText;
    isUserReading = true;

    el.innerHTML = `
        <input type="text" value="${oldText}" id="edit-${commentId}" 
        style="width:100%; background:rgba(255,255,255,0.1); border:1px solid #444; color:white; padding:6px; border-radius:6px; outline:none;">
    `;

    const input = document.getElementById(`edit-${commentId}`);
    input.focus();

    const save = () => {
        el.innerText = input.value.trim() || oldText;
        isUserReading = false;
    };

    input.onblur = save;
    input.onkeydown = (e) => {
        if (e.key === "Enter") save();
        if (e.key === "Escape") { el.innerText = oldText; isUserReading = false; }
    };
}

function deleteComment(commentId) {
    if (confirm("Supprimer ce commentaire ?")) {
        const el = document.getElementById(`comment-${commentId}`);
        if (el) el.remove();
    }
}

function setupReply(commentId) {
    const sector = document.getElementById(`reply-sector-${commentId}`);
    if (!sector || document.getElementById(`input-${commentId}`)) return;

    sector.innerHTML += `
        <div class="reply-input">
            <input type="text" id="input-${commentId}" placeholder="Répondre...">
            <button onclick="this.parentElement.remove()">✕</button>
        </div>
    `;
    document.getElementById(`input-${commentId}`).focus();
}