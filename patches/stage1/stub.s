# Stage 1 hook for E-M5 II 4.1 (build 4100).
#
# Entered by a jmp that replaces the two instructions at HOOK (0x604df2b6):
#     mov  (56,a2),d0
#     btst 0x64202e,d0
#
# On entry, as left by the stock selector at 0x604df257:
#     a2 = processing context
#     a3 = request, loaded from (4,a2)
#     d2 = request + 12, read again by the stock path. Keep it.
#     d3 = not saved by this function. Do not touch it.
# d0, d1, a0 and a1 are free: the stock path reloads each before use.
#
# Symbols supplied by the build: CARRIER_MODE, COLOR_TABLE, SAT_VALUES,
# BUILDER, RESUME_STOCK, EXIT_CLEAR_DIRTY, EXIT_CACHE_TAG.

	.text
	.global	stub
stub:
	# Picture mode, composed the same way the stock lookup does it:
	# byte 8 << 24 | byte 9 << 16 | halfword 10.
	movbu	(8,a3),d1
	asl	24,d1
	movbu	(9,a3),d0
	asl	16,d0
	or	d0,d1
	movhu	(10,a3),d0
	or	d0,d1
	cmp	CARRIER_MODE,d1
	bne	stock

	# COLOR case. Same arguments as the PEN-F call at 0x604f7506.
	mov	(12,a2),d1
	mov	SAT_VALUES,a1
	movhu	(COLOR_TABLE+3024),d0
	mov	COLOR_TABLE,a0
	call	BUILDER,[d2,d3,a2,a3],96

	# Same tail as the PEN-F after its builder call, using this body's
	# own copies of the two exits.
	mov	(56,a2),d0
	btst	2,d0
	beq	clear_dirty
	jmp	EXIT_CACHE_TAG
clear_dirty:
	jmp	EXIT_CLEAR_DIRTY

stock:
	# The two displaced instructions. jmp leaves the flags alone, so the
	# beq at RESUME_STOCK still sees this btst.
	mov	(56,a2),d0
	btst	0x64202e,d0
	jmp	RESUME_STOCK
