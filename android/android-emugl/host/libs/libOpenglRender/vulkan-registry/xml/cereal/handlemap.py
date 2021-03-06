# Copyright (c) 2018 The Android Open Source Project
# Copyright (c) 2018 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from copy import deepcopy

from .common.codegen import CodeGen
from .common.vulkantypes import \
        VulkanAPI, makeVulkanTypeSimple, iterateVulkanType

from .wrapperdefs import VulkanWrapperGenerator

class HandleMapCodegen(object):
    def __init__(self, cgen, inputVar, handlemapVarName, prefix, isHandleFunc):
        self.cgen = cgen
        self.inputVar = inputVar
        self.prefix = prefix
        self.handlemapVarName = handlemapVarName

        def makeAccess(varName, asPtr = True):
            return lambda t: self.cgen.generalAccess(t, parentVarName = varName, asPtr = asPtr)

        def makeLengthAccess(varName):
            return lambda t: self.cgen.generalLengthAccess(t, parentVarName = varName)

        self.exprAccessor = makeAccess(self.inputVar)
        self.exprAccessorValue = makeAccess(self.inputVar, asPtr = False)
        self.lenAccessor = makeLengthAccess(self.inputVar)

        self.checked = False
        self.isHandleFunc = isHandleFunc

    def needSkip(self, vulkanType):
        if vulkanType.isNextPointer():
            return True
        return False

    def makeCastExpr(self, vulkanType):
        return "(%s)" % (
            self.cgen.makeCTypeDecl(vulkanType, useParamName=False))

    def asNonConstCast(self, access, vulkanType):
        if vulkanType.staticArrExpr:
            casted = "%s(%s)" % (self.makeCastExpr(vulkanType.getForAddressAccess().getForNonConstAccess()), access)
        elif vulkanType.accessibleAsPointer():
            casted = "%s(%s)" % (self.makeCastExpr(vulkanType.getForNonConstAccess()), access)
        else:
            casted = "%s(%s)" % (self.makeCastExpr(vulkanType.getForAddressAccess().getForNonConstAccess()), access)
        return casted

    def onCheck(self, vulkanType):
        pass

    def endCheck(self, vulkanType):
        pass

    def onCompoundType(self, vulkanType):

        if self.needSkip(vulkanType):
            self.cgen.line("// TODO: Unsupported : %s" %
                           self.cgen.makeCTypeDecl(vulkanType))
            return

        access = self.exprAccessor(vulkanType)
        lenAccess = self.lenAccessor(vulkanType)

        isPtr = vulkanType.pointerIndirectionLevels > 0

        if isPtr:
            self.cgen.beginIf(access)

        if lenAccess is not None:

            loopVar = "i"
            access = "%s + %s" % (access, loopVar)
            forInit = "uint32_t %s = 0" % loopVar
            forCond = "%s < (uint32_t)%s" % (loopVar, lenAccess)
            forIncr = "++%s" % loopVar

            self.cgen.beginFor(forInit, forCond, forIncr)

        accessCasted = self.asNonConstCast(access, vulkanType)
        self.cgen.funcCall(None, self.prefix + vulkanType.typeName,
                           [self.handlemapVarName, accessCasted])

        if lenAccess is not None:
            self.cgen.endFor()

        if isPtr:
            self.cgen.endIf()

    def onString(self, vulkanType):
        pass

    def onStringArray(self, vulkanType):
        pass

    def onStaticArr(self, vulkanType):
        if not self.isHandleFunc(vulkanType):
            return

        accessLhs = self.exprAccessor(vulkanType)
        lenAccess = self.lenAccessor(vulkanType)

        self.cgen.stmt("%s->mapHandles_%s(%s%s, %s)" % \
            (self.handlemapVarName, vulkanType.typeName,
             self.makeCastExpr(vulkanType.getForAddressAccess().getForNonConstAccess()),
             accessLhs, lenAccess))

    def onPointer(self, vulkanType):
        if not self.isHandleFunc(vulkanType):
            return

        if self.needSkip(vulkanType):
            return

        access = self.exprAccessor(vulkanType)
        lenAccess = self.lenAccessor(vulkanType)

        self.cgen.beginIf(access)

        self.cgen.stmt( \
            "%s->mapHandles_%s(%s%s, %s)" % \
            (self.handlemapVarName,
             vulkanType.typeName,
             self.makeCastExpr(vulkanType.getForNonConstAccess()),
             access,
             lenAccess))

        self.cgen.endIf()

    def onValue(self, vulkanType):
        if not self.isHandleFunc(vulkanType):
            return
        access = self.exprAccessor(vulkanType)
        self.cgen.stmt(
            "%s->mapHandles_%s(%s%s)" % \
            (self.handlemapVarName, vulkanType.typeName,
             self.makeCastExpr(vulkanType.getForAddressAccess().getForNonConstAccess()),
             access))

class VulkanHandleMap(VulkanWrapperGenerator):
    def __init__(self, module, typeInfo):
        VulkanWrapperGenerator.__init__(self, module, typeInfo)

        self.codegen = CodeGen()

        self.handlemapPrefix = "handlemap_"
        self.toMapVar = "toMap"
        self.handlemapVarName = "handlemap"
        self.handlemapParam = \
            makeVulkanTypeSimple(False, "VulkanHandleMapping", 1,
                                 self.handlemapVarName)
        self.voidType = makeVulkanTypeSimple(False, "void", 0)

        self.handlemapCodegen = \
            HandleMapCodegen(
                None,
                self.toMapVar,
                self.handlemapVarName,
                self.handlemapPrefix,
                lambda vtype : typeInfo.isHandleType(vtype))

        self.knownDefs = {}

    def onGenType(self, typeXml, name, alias):
        VulkanWrapperGenerator.onGenType(self, typeXml, name, alias)

        if name in self.knownDefs:
            return

        category = self.typeInfo.categoryOf(name)

        if category in ["struct", "union"] and not alias:

            structInfo = self.typeInfo.structs[name]

            typeFromName = \
                lambda varname: \
                    makeVulkanTypeSimple(varname == "from", name, 1, varname)

            handlemapParams = \
                [self.handlemapParam] + \
                list(map(typeFromName, [self.toMapVar]))
                
            handlemapPrototype = \
                VulkanAPI(self.handlemapPrefix + name,
                          self.voidType,
                          handlemapParams)

            def funcDefGenerator(cgen):
                self.handlemapCodegen.cgen = cgen
                for member in structInfo.members:
                    iterateVulkanType(self.typeInfo, member,
                                      self.handlemapCodegen)

            self.module.appendHeader(
                self.codegen.makeFuncDecl(handlemapPrototype))
            self.module.appendImpl(
                self.codegen.makeFuncImpl(handlemapPrototype, funcDefGenerator))

    def onGenCmd(self, cmdinfo, name, alias):
        VulkanWrapperGenerator.onGenCmd(self, cmdinfo, name, alias)
