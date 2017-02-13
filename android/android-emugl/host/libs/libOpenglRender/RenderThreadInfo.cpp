/*
* Copyright (C) 2011 The Android Open Source Project
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
* http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*/

#include "RenderThreadInfo.h"

#include "emugl/common/lazy_instance.h"
#include "emugl/common/thread_store.h"
#include "FrameBuffer.h"

namespace {

class ThreadInfoStore : public ::emugl::ThreadStore {
public:
    ThreadInfoStore() : ::emugl::ThreadStore(NULL) {}
};

}  // namespace

static ::emugl::LazyInstance<ThreadInfoStore> s_tls = LAZY_INSTANCE_INIT;

RenderThreadInfo::RenderThreadInfo() {
    s_tls->set(this);
}

RenderThreadInfo::~RenderThreadInfo() {
    s_tls->set(NULL);
}

RenderThreadInfo* RenderThreadInfo::get() {
    return static_cast<RenderThreadInfo*>(s_tls->get());
}

void RenderThreadInfo::onSave(android::base::Stream* stream) {
    if (currContext) {
        stream->putBe32(currContext->getHndl());
    } else {
        stream->putBe32(0);
    }
    if (currDrawSurf) {
        stream->putBe32(currDrawSurf->getHndl());
    } else {
        stream->putBe32(0);
    }
    if (currReadSurf) {
        stream->putBe32(currReadSurf->getHndl());
    } else {
        stream->putBe32(0);
    }
    // TODO: save other stuff
}

bool RenderThreadInfo::onLoad(android::base::Stream* stream) {
    FrameBuffer* fb = FrameBuffer::getFB();
    assert(fb);
    HandleType ctxHndl = stream->getBe32();
    HandleType drawSurf = stream->getBe32();
    HandleType readSurf = stream->getBe32();
    currContext = fb->getContext(ctxHndl);
    currDrawSurf = fb->getWindowSurface(drawSurf);
    currReadSurf = fb->getWindowSurface(readSurf);
    // TODO: load other stuff
    return true;
}
