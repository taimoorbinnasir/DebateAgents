import jsPDF from "jspdf"
import html2canvas from "html2canvas"

export async function exportElementToPDF(element, filename = "debate_analysis.pdf") {
  if (!element) return

  const canvas = await html2canvas(element, {
    scale: 2,
    backgroundColor: "#ffffff",
    useCORS: true
  })

  const imgData = canvas.toDataURL("image/png")
  const pdf = new jsPDF("p", "mm", "a4")
  const pageWidth  = pdf.internal.pageSize.getWidth()
  const pageHeight = pdf.internal.pageSize.getHeight()
  const imgWidth  = pageWidth - 20
  const imgHeight = (canvas.height * imgWidth) / canvas.width

  let heightLeft = imgHeight
  let position = 10

  // First page
  pdf.addImage(imgData, "PNG", 10, position, imgWidth, imgHeight)
  heightLeft -= (pageHeight - 20)

  // Add extra pages if content overflows one page
  while (heightLeft > 0) {
    position = heightLeft - imgHeight + 10
    pdf.addPage()
    pdf.addImage(imgData, "PNG", 10, position, imgWidth, imgHeight)
    heightLeft -= (pageHeight - 20)
  }

  pdf.save(filename)
}