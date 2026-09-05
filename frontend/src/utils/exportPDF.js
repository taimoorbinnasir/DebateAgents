import jsPDF from "jspdf"
import html2canvas from "html2canvas"

function findBreakPoint(canvas, targetY, searchRange = 100) {
  const ctx = canvas.getContext("2d")
  const width = canvas.width

  // Search backwards from targetY for a row that's mostly white (safe to cut)
  for (let y = targetY; y > Math.max(0, targetY - searchRange); y--) {
    const rowData = ctx.getImageData(0, y, width, 1).data
    let whitePixels = 0

    // Sample every 4th pixel for speed
    for (let x = 0; x < width; x += 4) {
      const idx = x * 4
      const r = rowData[idx], g = rowData[idx + 1], b = rowData[idx + 2]
      if (r > 245 && g > 245 && b > 245) whitePixels++
    }

    const sampledCount = width / 4
    if (whitePixels / sampledCount > 0.98) {
      return y  // found a clean row to cut at
    }
  }
  // No clean break found within range — fall back to the original target
  return targetY
}

export async function exportElementToPDF(element, filename = "debate_analysis.pdf") {
  if (!element) return

  const rawCanvas = await html2canvas(element, {
    scale: 2,
    backgroundColor: "#ffffff",
    useCORS: true
  })

  // Pad the bottom with white space so the last slice never cuts exactly at content's end
  const padding = 40  // px, in canvas scale
  const canvas = document.createElement("canvas")
  canvas.width = rawCanvas.width
  canvas.height = rawCanvas.height + padding
  const paddedCtx = canvas.getContext("2d")
  paddedCtx.fillStyle = "#ffffff"
  paddedCtx.fillRect(0, 0, canvas.width, canvas.height)
  paddedCtx.drawImage(rawCanvas, 0, 0)

  const pdf = new jsPDF("p", "mm", "a4")
  const pageWidth  = pdf.internal.pageSize.getWidth()
  const pageHeight = pdf.internal.pageSize.getHeight()
  const margin = 10
  const usableWidth  = pageWidth - margin * 2
  const usableHeight = pageHeight - margin * 2

  const pxPerMm = canvas.width / usableWidth
  const maxSliceHeight = usableHeight * pxPerMm

  let renderedHeight = 0
  let isFirstPage = true

  while (renderedHeight < canvas.height) {
    let targetEnd = Math.min(renderedHeight + maxSliceHeight, canvas.height)

    if (targetEnd < canvas.height) {
      targetEnd = findBreakPoint(canvas, targetEnd)
    }

    const sliceHeight = targetEnd - renderedHeight
    if (sliceHeight <= 0) break

    const pageCanvas = document.createElement("canvas")
    pageCanvas.width = canvas.width
    pageCanvas.height = sliceHeight

    const ctx = pageCanvas.getContext("2d")
    ctx.drawImage(
      canvas,
      0, renderedHeight,
      canvas.width, sliceHeight,
      0, 0,
      canvas.width, sliceHeight
    )

    const sliceImgData = pageCanvas.toDataURL("image/png")
    const sliceImgHeightMm = sliceHeight / pxPerMm

    if (!isFirstPage) pdf.addPage()
    pdf.addImage(sliceImgData, "PNG", margin, margin, usableWidth, sliceImgHeightMm)

    renderedHeight = targetEnd
    isFirstPage = false
  }

  pdf.save(filename)
}