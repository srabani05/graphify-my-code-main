// codegraph CPG dump — paths are baked in by codegraph/languages/joern.py
// Run: joern --script <this file>   (no console needed)
importCpg("final-joern/.joern-work/petclinic-src.cpg0.bin")

def esc(s: String): String =
  if (s == null) "" else s.replace("\\", "\\\\").replace("\"", "\\\"")
    .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
def q(s: String): String = "\"" + esc(s) + "\""
def one(t: Iterator[String]): String = t.toList.headOption.getOrElse("")

val out = new java.io.PrintWriter("final-joern/.joern-work/petclinic-src.dump0.jsonl")
var nMethod = 0
var nCall = 0
var nType = 0
var nMember = 0

// --- type declarations (classes / interfaces / enums) + their members ---
cpg.typeDecl.filterNot(_.isExternal).foreach { t =>
  val tf = t.fullName
  val file = t.filename
  val line = t.lineNumber.getOrElse(0)
  val sup = t.inheritsFromTypeFullName.filterNot(_ == "ANY").toList.mkString(",")
  out.println(s"""{"t":"type","fullName":${q(tf)},"name":${q(t.name)},"file":${q(file)},"line":$line,"super":${q(sup)}}""")
  nType += 1
  t.member.foreach { m =>
    out.println(s"""{"t":"member","owner":${q(tf)},"name":${q(m.name)},"type":${q(m.typeFullName)},"file":${q(file)},"line":${m.lineNumber.getOrElse(0)}}""")
    nMember += 1
  }
}

// --- methods (keep stubs declared in-repo: interface methods have no body;
// external stubs have an empty filename) ---
cpg.method.filterNot(m => m.isStub && m.filename.isEmpty).foreach { m =>
  val cls = one(m.typeDecl.fullName)
  out.println(s"""{"t":"method","fullName":${q(m.fullName)},"name":${q(m.name)},"signature":${q(m.signature)},"class":${q(cls)},"file":${q(m.filename)},"line":${m.lineNumber.getOrElse(0)}}""")
  nMethod += 1
}

// --- calls (skip internal operators) ---
cpg.call.filterNot(_.name.startsWith("<operator>")).foreach { c =>
  val caller = c.method.fullName
  val file = one(c.file.name)
  out.println(s"""{"t":"call","caller":${q(caller)},"callee":${q(c.methodFullName)},"name":${q(c.name)},"code":${q(c.code)},"file":${q(file)},"line":${c.lineNumber.getOrElse(0)}}""")
  nCall += 1
}

// --- annotations (framework layer: Spring / MyBatis / JMS) ---
var nAnn = 0
cpg.annotation.foreach { a =>
  val m = one(a.method.fullName)
  val t = one(a.typeDecl.fullName)
  out.println(s"""{"t":"annotation","name":${q(a.name)},"code":${q(a.code)},"method":${q(m)},"type":${q(t)}}""")
  nAnn += 1
}

out.close()
println(s"DUMP_DONE methods=$nMethod calls=$nCall types=$nType members=$nMember ann=$nAnn")
